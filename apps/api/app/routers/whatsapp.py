"""WhatsApp endpoint'leri.

- Webhook (Meta'dan gelen mesajları al)
- Inbox list (tüm konuşmalar)
- Conversation detail (bir kişiyle tüm mesajlar)
- Send message (manuel cevap)
- AI draft (AI taslağı al)
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth.dependencies import get_current_user
from app.config import settings

# Yeni modeller
from app.models_whatsapp import (
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppWebhookLog,
)
from app.services.whatsapp_client import whatsapp_client
from app.services.ai_assistant import ai_assistant, decide_action


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


# ─────────────────────────────────────────────────────────────
# WEBHOOK — Meta'dan gelen mesajlar buraya düşer
# ─────────────────────────────────────────────────────────────

@router.get("/webhook")
async def webhook_verify(request: Request):
    """Meta webhook doğrulama.

    Meta webhook kurulumu sırasında challenge parametresiyle bu endpoint'i çağırır.
    Verify token doğruysa challenge'ı geri döndürmeliyiz.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_webhook_verify_token:
        logger.info("WhatsApp webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("WhatsApp webhook verification failed: mode=%s token_match=%s",
                   mode, token == settings.whatsapp_webhook_verify_token)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def webhook_receive(request: Request, db: Session = Depends(get_db)):
    """Meta'dan gelen mesajları işle.

    ÖNEMLİ: Meta 20 saniye içinde 200 OK bekliyor.
    Bu yüzden:
    1. Payload'ı kaydet (hızlı)
    2. Mesajı veritabanına yaz (hızlı)
    3. 200 döndür
    4. AI analizi + auto-reply background'da (async)

    Üretim ortamında bu arkaplan işi Celery/RQ queue'ya gitmeli. Şimdilik async task.
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Webhook payload parse failed: %s", e)
        return {"ok": True}  # Meta'nın retry'ını engelle

    # Audit log
    log = WhatsAppWebhookLog(payload=payload)
    db.add(log)
    db.commit()

    # Meta payload yapısı:
    # { "entry": [{"changes": [{"value": {"messages": [...], "contacts": [...]}}]}] }
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Mesaj geldi mi?
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])

                # Contacts map: phone → profile_name
                contact_map = {
                    c.get("wa_id"): c.get("profile", {}).get("name")
                    for c in contacts
                }

                for msg in messages:
                    await _process_inbound_message(db, msg, contact_map)

                # Status update geldi mi? (delivered, read, failed)
                statuses = value.get("statuses", [])
                for st in statuses:
                    _process_status_update(db, st)

        log.processed = True
        db.commit()

    except Exception as e:
        logger.exception("Webhook processing error: %s", e)
        log.error = str(e)
        db.commit()

    return {"ok": True}


async def _process_inbound_message(db: Session, msg: dict, contact_map: dict):
    """Gelen tek bir mesajı DB'ye yaz + AI analizine gönder."""
    wa_id = msg.get("from")  # Müşterinin numarası
    wamid = msg.get("id")  # Meta mesaj ID
    msg_type = msg.get("type", "text")  # text, image, audio, document, ...

    if not wa_id or not wamid:
        return

    # Daha önce işlendi mi?
    existing = db.query(WhatsAppMessage).filter(
        WhatsAppMessage.meta_message_id == wamid
    ).first()
    if existing:
        return

    # Konuşma var mı?
    conv = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.phone == wa_id
    ).first()

    profile_name = contact_map.get(wa_id)

    if not conv:
        conv = WhatsAppConversation(
            phone=wa_id,
            profile_name=profile_name,
            contact_name=profile_name,  # Varsayılan olarak profil adını kullan
            last_message_at=datetime.utcnow(),
        )
        db.add(conv)
        db.flush()  # ID al
    else:
        if profile_name and not conv.profile_name:
            conv.profile_name = profile_name

    # İçerik çıkar
    content = ""
    media_url = None
    media_mime = None

    if msg_type == "text":
        content = msg.get("text", {}).get("body", "")
    elif msg_type in ("image", "audio", "video", "document", "sticker"):
        media = msg.get(msg_type, {})
        media_id = media.get("id")
        content = media.get("caption", f"[{msg_type}]")
        media_mime = media.get("mime_type")
        if media_id:
            # Gerçek URL'i sonra indir (Meta'dan geçici URL)
            try:
                media_url = await whatsapp_client.get_media_url(media_id)
            except Exception as e:
                logger.warning("Media URL fetch failed: %s", e)
    elif msg_type == "location":
        loc = msg.get("location", {})
        content = f"[Konum: {loc.get('latitude')},{loc.get('longitude')}] {loc.get('name', '')}"
    else:
        content = f"[{msg_type}]"

    # Mesajı kaydet
    message = WhatsAppMessage(
        conversation_id=conv.id,
        meta_message_id=wamid,
        direction="inbound",
        content_type=msg_type,
        content=content,
        media_url=media_url,
        media_mime=media_mime,
        status="delivered",
    )
    db.add(message)

    # Konuşmayı güncelle
    conv.last_message_at = datetime.utcnow()
    conv.last_message_preview = content[:280]
    conv.unread_count = (conv.unread_count or 0) + 1

    db.commit()
    db.refresh(message)
    db.refresh(conv)

    # Okundu olarak işaretle (Meta'da mavi tik)
    try:
        await whatsapp_client.mark_as_read(wamid)
    except Exception:
        pass

    # AI analizi başlat (text mesajlar için)
    if msg_type == "text" and content.strip():
        await _run_ai_analysis(db, message, conv)


async def _run_ai_analysis(db: Session, message: WhatsAppMessage, conv: WhatsAppConversation):
    """Mesajı AI ile analiz et, gerekirse otomatik cevap gönder."""
    if not ai_assistant.is_configured():
        return

    # Konuşma geçmişi (son 10 mesaj)
    history_msgs = db.query(WhatsAppMessage).filter(
        WhatsAppMessage.conversation_id == conv.id,
        WhatsAppMessage.id != message.id,
    ).order_by(WhatsAppMessage.created_at.desc()).limit(10).all()

    history = []
    for m in reversed(history_msgs):
        history.append({
            "role": "user" if m.direction == "inbound" else "assistant",
            "content": m.content,
        })

    # Analiz
    try:
        analysis = await ai_assistant.analyze_message(
            message_text=message.content,
            conversation_history=history,
            contact_name=conv.contact_name or conv.profile_name,
        )
    except Exception as e:
        logger.exception("AI analysis failed: %s", e)
        return

    # Sonucu kaydet
    message.ai_intent = analysis.get("intent")
    message.ai_sentiment = analysis.get("sentiment")
    message.ai_language = analysis.get("language")
    message.ai_confidence = analysis.get("confidence")
    message.ai_summary = analysis.get("summary")
    message.ai_draft = analysis.get("draft_reply")
    message.ai_draft_confidence = analysis.get("confidence")

    # Aciliyet varsa konuşmayı işaretle
    if analysis.get("requires_human") or analysis.get("sentiment") == "urgent":
        conv.needs_attention = True

    db.commit()

    # Karar ver: otomatik gönder mi, taslak mı?
    action = decide_action(analysis, conv.ai_mode)

    if action == "auto_reply" and analysis.get("draft_reply"):
        try:
            sent = await whatsapp_client.send_text(
                to=conv.phone,
                body=analysis["draft_reply"],
                reply_to=message.meta_message_id,
            )
            out_wamid = sent.get("messages", [{}])[0].get("id")

            # Outbound mesajı DB'ye yaz
            out_msg = WhatsAppMessage(
                conversation_id=conv.id,
                meta_message_id=out_wamid,
                direction="outbound",
                content_type="text",
                content=analysis["draft_reply"],
                ai_auto_sent=True,
                sent_by="ai",
                status="sent",
                reply_to_id=message.id,
            )
            db.add(out_msg)
            conv.last_message_at = datetime.utcnow()
            conv.last_message_preview = analysis["draft_reply"][:280]
            db.commit()

            logger.info("Auto-replied to %s: %s", conv.phone, analysis["draft_reply"][:50])
        except Exception as e:
            logger.exception("Auto-reply send failed: %s", e)


def _process_status_update(db: Session, status: dict):
    """Meta'dan gelen sent/delivered/read/failed bildirimleri."""
    wamid = status.get("id")
    status_value = status.get("status")  # sent | delivered | read | failed

    if not wamid or not status_value:
        return

    msg = db.query(WhatsAppMessage).filter(
        WhatsAppMessage.meta_message_id == wamid
    ).first()

    if msg:
        msg.status = status_value
        if status_value == "failed":
            errors = status.get("errors", [])
            if errors:
                msg.error_message = errors[0].get("message", "")
        db.commit()


# ─────────────────────────────────────────────────────────────
# Inbox API — Frontend için
# ─────────────────────────────────────────────────────────────

class ConversationSummary(BaseModel):
    id: int
    phone: str
    contact_name: Optional[str]
    profile_name: Optional[str]
    last_message_at: datetime
    last_message_preview: Optional[str]
    unread_count: int
    ai_mode: str
    is_vip: bool
    needs_attention: bool
    tags: Optional[list]

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    direction: str
    content_type: str
    content: str
    media_url: Optional[str]
    ai_intent: Optional[str]
    ai_sentiment: Optional[str]
    ai_confidence: Optional[float]
    ai_draft: Optional[str]
    ai_auto_sent: bool
    status: str
    sent_by: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    needs_attention: Optional[bool] = None,
    workspace_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(WhatsAppConversation).order_by(
        WhatsAppConversation.last_message_at.desc()
    )
    if needs_attention is not None:
        q = q.filter(WhatsAppConversation.needs_attention == needs_attention)
    if workspace_id:
        q = q.filter(WhatsAppConversation.workspace_id == workspace_id)
    return q.limit(limit).all()


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageResponse])
def get_messages(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.id == conv_id
    ).first()
    if not conv:
        raise HTTPException(404, "Konuşma bulunamadı")

    # Okundu olarak işaretle
    conv.unread_count = 0
    db.commit()

    messages = db.query(WhatsAppMessage).filter(
        WhatsAppMessage.conversation_id == conv_id
    ).order_by(WhatsAppMessage.created_at.asc()).all()

    return messages


class SendMessageRequest(BaseModel):
    body: str
    reply_to_message_id: Optional[int] = None


@router.post("/conversations/{conv_id}/send")
async def send_message(
    conv_id: int,
    data: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.id == conv_id
    ).first()
    if not conv:
        raise HTTPException(404, "Konuşma bulunamadı")

    # Reply to?
    reply_to_wamid = None
    if data.reply_to_message_id:
        reply_msg = db.query(WhatsAppMessage).filter(
            WhatsAppMessage.id == data.reply_to_message_id
        ).first()
        if reply_msg:
            reply_to_wamid = reply_msg.meta_message_id

    try:
        sent = await whatsapp_client.send_text(
            to=conv.phone,
            body=data.body,
            reply_to=reply_to_wamid,
        )
        out_wamid = sent.get("messages", [{}])[0].get("id")
    except Exception as e:
        raise HTTPException(500, f"Gönderim başarısız: {e}")

    out_msg = WhatsAppMessage(
        conversation_id=conv.id,
        meta_message_id=out_wamid,
        direction="outbound",
        content_type="text",
        content=data.body,
        sent_by="user",
        status="sent",
        reply_to_id=data.reply_to_message_id,
    )
    db.add(out_msg)
    conv.last_message_at = datetime.utcnow()
    conv.last_message_preview = data.body[:280]
    db.commit()
    db.refresh(out_msg)

    return {"ok": True, "message_id": out_msg.id}


@router.post("/messages/{msg_id}/approve-draft")
async def approve_ai_draft(
    msg_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI'ın taslak cevabını onaylayıp gönder."""
    msg = db.query(WhatsAppMessage).filter(WhatsAppMessage.id == msg_id).first()
    if not msg or not msg.ai_draft:
        raise HTTPException(404, "Taslak bulunamadı")

    conv = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.id == msg.conversation_id
    ).first()

    try:
        sent = await whatsapp_client.send_text(
            to=conv.phone,
            body=msg.ai_draft,
            reply_to=msg.meta_message_id,
        )
        out_wamid = sent.get("messages", [{}])[0].get("id")
    except Exception as e:
        raise HTTPException(500, f"Gönderim başarısız: {e}")

    out_msg = WhatsAppMessage(
        conversation_id=conv.id,
        meta_message_id=out_wamid,
        direction="outbound",
        content_type="text",
        content=msg.ai_draft,
        ai_auto_sent=False,
        sent_by="ai",  # AI yazdı ama user onayladı
        status="sent",
        reply_to_id=msg.id,
    )
    db.add(out_msg)
    conv.last_message_at = datetime.utcnow()
    conv.last_message_preview = msg.ai_draft[:280]
    db.commit()

    return {"ok": True}


class UpdateConversationRequest(BaseModel):
    ai_mode: Optional[str] = None
    contact_name: Optional[str] = None
    is_vip: Optional[bool] = None
    needs_attention: Optional[bool] = None
    tags: Optional[list] = None
    workspace_id: Optional[int] = None


@router.patch("/conversations/{conv_id}")
def update_conversation(
    conv_id: int,
    data: UpdateConversationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.id == conv_id
    ).first()
    if not conv:
        raise HTTPException(404, "Konuşma bulunamadı")

    update = data.model_dump(exclude_none=True)
    allowed = {"ai_mode", "contact_name", "is_vip", "needs_attention", "tags", "workspace_id"}
    for k, v in update.items():
        if k in allowed:
            setattr(conv, k, v)

    db.commit()
    return {"ok": True}


@router.get("/stats")
def inbox_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dashboard için inbox özet istatistikleri."""
    total = db.query(WhatsAppConversation).count()
    unread = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.unread_count > 0
    ).count()
    attention = db.query(WhatsAppConversation).filter(
        WhatsAppConversation.needs_attention == True
    ).count()

    return {
        "total_conversations": total,
        "unread_conversations": unread,
        "needs_attention": attention,
    }
