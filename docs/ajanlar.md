# Ajan düzeni — pahalı model yalnız kritik işte

Ana oturum **Sonnet 5.5** ile açılır (`.claude/settings.json` → `"model": "sonnet"`).
Fable 5.1 yalnız iki ajanda çalışır: planlama (`mimar`) ve kritik denetim
(`kritik-denetci`). Ajan tanımları `.claude/agents/` altındadır.

| Ajan | Model | İş |
|---|---|---|
| `mimar` | Fable 5.1 | Ana sayfa tema/dizayn projelendirmesi + SEO düzeni; `docs/plan/` altına görev listesi yazar, kod yazmaz |
| `uygulayici` | Sonnet 5.5 | Plandaki `@uygulayici` görevleri, günlük geliştirme |
| `rutin-isci` | Haiku 5.5 | Build/test, çeviri sözlüğü, betikler, küçük düzeltmeler |
| `kritik-denetci` | Fable 5.1 | Ödeme/fiyat/güvenlik/kişisel veri/hukuki metin değişikliklerini commit öncesi denetler |

## Akış
1. Tasarım/tema/SEO işi gelince ana oturum `mimar`'ı çağırır → plan dosyası
   `docs/plan/<tarih>-<konu>.md` oluşur.
2. Ana oturum plandaki görevleri etiketine göre `uygulayici` ve `rutin-isci`'ye
   dağıtır (alt ajanlar başka ajan çağıramaz; dağıtımı ana oturum yapar).
3. Kritik alana dokunulduysa commit öncesi `kritik-denetci` çalışır.
4. Ana oturum commit'ler ve push eder.

## Kurallar
- Fable'ı ana oturumda kullanma; gerekiyorsa geçici `/model fable`, iş bitince `/model sonnet`.
- Basit iş (tek dosya, net istek) ajansız, doğrudan ana oturumda yapılır —
  her ajan sıfırdan bağlam topladığı için gereksiz ajan da kredi harcar.
- Planı olmayan küçük tema düzeltmesi için `mimar` çağrılmaz.
