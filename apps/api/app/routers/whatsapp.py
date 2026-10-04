"""WhatsApp endpoint'leri.

- Webhook (Meta'dan gelen mesajları al)
- Inbox list (tüm konuşmalar)
- Conversation detail (bir kişiyle tüm mesajlar)
- Send message (manuel cevap)
- AI draft (AI taslağı al)
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
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
from app.services import briefing


def _wants_briefing(message) -> bool:
    """Şablon düğmesi ya da "brifing" yazısı."""
    text = (message.content or "").strip().lower()
    return message.content_type in ("button", "interactive") or text in ("brifing", "brifingi gönder")


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


def verify_signature(raw_body: bytes, header: Optional[str]) -> bool:
    """Meta imzası: X-Hub-Signature-256 = "sha256=" + HMAC-SHA256(app secret, ham gövde).

    App secret tanımlı değilse imza doğrulanamaz: üretimde istek REDDEDİLİR
    (sahte webhook ile mesaj yazdırılmasın), geliştirmede uyarıyla kabul edilir.
    """
    secret = settings.whatsapp_app_secret
    if not secret:
        if settings.is_production:
            logger.error("WHATSAPP_APP_SECRET tanımlı değil — webhook reddedildi")
            return False
        logger.warning("WHATSAPP_APP_SECRET yok — imza doğrulanmadan kabul edildi (geliştirme)")
        return True
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[len("sha256="):])


@router.post("/webhook")
async def webhook_receive(
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Meta'dan gelen mesajları işle.

    Meta 20 saniye içinde 200 OK bekler. Bu yüzden istek içinde yalnız imza
    doğrulanır, payload ve mesaj veritabanına yazılır; okundu işareti ve AI
    analizi/otomatik cevap yanıt döndükten SONRA arka planda çalışır.
    """
    raw = await request.body()
    if not verify_signature(raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=403, detail="Geçersiz imza")

    try:
        payload = json.loads(raw)
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
                    saved = await _process_inbound_message(db, msg, contact_map)
                    if saved is not None:
                        background.add_task(_after_inbound, saved)

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


async def _process_inbound_message(db: Session, msg: dict, contact_map: dict) -> Optional[int]:
    """Gelen tek bir mesajı DB'ye yaz; arka plan işi için mesaj id'sini döndür."""
    wa_id = msg.get("from")  # Müşterinin numarası
    wamid = msg.get("id")  # Meta mesaj ID
    msg_type = msg.get("type", "text")  # text, image, audio, document, ...

    if not wa_id or not wamid:
        return None

    # Daha önce işlendi mi?
    existing = db.query(WhatsAppMessage).filter(
        WhatsAppMessage.meta_message_id == wamid
    ).first()
    if existing:
        return None

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
    elif msg_type == "button":
        # Şablondaki hızlı yanıt düğmesi ("Brifingi gönder")
        content = (msg.get("button") or {}).get("text") or "[button]"
    elif msg_type == "interactive":
        it = msg.get("interactive") or {}
        content = ((it.get("button_reply") or it.get("list_reply") or {}).get("title")) or "[interactive]"
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
    return message.id


async def _after_inbound(message_id: int):
    """Arka plan: okundu işareti + AI analizi. İstek oturumu kapandığı için
    kendi veritabanı oturumunu açar."""
    db = SessionLocal()
    try:
        message = db.query(WhatsAppMessage).filter(WhatsAppMessage.id == message_id).first()
        if not message:
            return
        conv = message.conversation

        # Okundu olarak işaretle (Meta'da mavi tik)
        try:
            await whatsapp_client.mark_as_read(message.meta_message_id)
        except Exception:
            pass

        # Sahibin (JARVIS_OWNER_PHONE) mesajı müşteri asistanına GİTMEZ
        if briefing.owner_phone() and conv.phone == briefing.owner_phone():
            if _wants_briefing(message):
                await briefing.send_full_to_owner(db)
            return

        # AI analizi (text mesajlar için)
        if message.content_type == "text" and (message.content or "").strip():
            await _run_ai_analysis(db, message, conv)
    except Exception as e:
        logger.exception("Inbound background job failed: %s", e)
    finally:
        db.close()


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
