import { useEffect, useState } from 'react'
import { GlassWater, ExternalLink, Music, Clock } from 'lucide-react'

/**
 * 30 ülkelik viski saati rotasyonu.
 * Her gün farklı bir ülkenin müziği — dünya turu.
 */
const COUNTRIES = [
  { name: 'USA', flag: '🇺🇸', tag: 'Country & Blues', hint: 'Johnny Cash, Chris Stapleton, Hank Williams' },
  { name: 'Türkiye', flag: '🇹🇷', tag: 'Türk Sanat & Arabesk', hint: 'Müslüm, Zeki Müren, Neşet Ertaş' },
  { name: 'Fas', flag: '🇲🇦', tag: 'Gnawa & Chaabi', hint: 'Nass El Ghiwane, Hamid El Kasri' },
  { name: 'İran', flag: '🇮🇷', tag: 'Klasik Pers', hint: 'Mohammad Reza Shajarian, Googoosh' },
  { name: 'UK', flag: '🇬🇧', tag: 'Rock & Soul', hint: 'Rolling Stones, Amy Winehouse, Adele' },
  { name: 'Fransa', flag: '🇫🇷', tag: 'Chanson', hint: 'Edith Piaf, Charles Aznavour, Stromae' },
  { name: 'Hindistan', flag: '🇮🇳', tag: 'Ghazal & Bollywood', hint: 'Jagjit Singh, Lata Mangeshkar' },
  { name: 'Brezilya', flag: '🇧🇷', tag: 'Bossa Nova & Samba', hint: 'João Gilberto, Caetano Veloso' },
  { name: 'İspanya', flag: '🇪🇸', tag: 'Flamenco', hint: 'Camarón, Paco de Lucía, Rosalía' },
  { name: 'Japonya', flag: '🇯🇵', tag: 'Enka & City Pop', hint: 'Mariya Takeuchi, Hikaru Utada' },
  { name: 'Rusya', flag: '🇷🇺', tag: 'Klasik & Şanson', hint: 'Vladimir Vysotsky, Alla Pugacheva' },
  { name: 'İtalya', flag: '🇮🇹', tag: 'Cantautori', hint: 'Lucio Battisti, Mina, Fabrizio De André' },
  { name: 'Arjantin', flag: '🇦🇷', tag: 'Tango', hint: 'Carlos Gardel, Astor Piazzolla' },
  { name: 'Mısır', flag: '🇪🇬', tag: 'Klasik Arap', hint: 'Umm Kulthum, Abdel Halim Hafez' },
  { name: 'Almanya', flag: '🇩🇪', tag: 'Liedermacher & Electronic', hint: 'Rammstein, Nena, Kraftwerk' },
  { name: 'Küba', flag: '🇨🇺', tag: 'Son & Bolero', hint: 'Buena Vista Social Club, Compay Segundo' },
  { name: 'Pakistan', flag: '🇵🇰', tag: 'Qawwali', hint: 'Nusrat Fateh Ali Khan, Rahat Fateh Ali Khan' },
  { name: 'İsveç', flag: '🇸🇪', tag: 'İndie & Pop', hint: 'ABBA, First Aid Kit, Robyn' },
  { name: 'Meksika', flag: '🇲🇽', tag: 'Mariachi & Ranchera', hint: 'Vicente Fernández, Chavela Vargas' },
  { name: 'Kore', flag: '🇰🇷', tag: 'Trot & İndie', hint: 'Na Hoon-a, IU, Cho Yong-pil' },
  { name: 'Nijerya', flag: '🇳🇬', tag: 'Afrobeat', hint: 'Fela Kuti, Burna Boy, Asa' },
  { name: 'Lübnan', flag: '🇱🇧', tag: 'Klasik Arap', hint: 'Fairuz, Marcel Khalife' },
  { name: 'İrlanda', flag: '🇮🇪', tag: 'Folk & Rock', hint: 'The Dubliners, U2, The Cranberries' },
  { name: 'Yunanistan', flag: '🇬🇷', tag: 'Rebetiko', hint: 'Mikis Theodorakis, Haris Alexiou' },
  { name: 'Kanada', flag: '🇨🇦', tag: 'Folk & Rock', hint: 'Leonard Cohen, Joni Mitchell, Neil Young' },
  { name: 'Portekiz', flag: '🇵🇹', tag: 'Fado', hint: 'Amália Rodrigues, Mariza' },
  { name: 'İsrail', flag: '🇮🇱', tag: 'Mizrahi', hint: 'Ofra Haza, Omer Adam, Shalom Hanoch' },
  { name: 'Gürcistan', flag: '🇬🇪', tag: 'Polifonik', hint: 'Hamlet Gonashvili, Rustavi Ensemble' },
  { name: 'Güney Afrika', flag: '🇿🇦', tag: 'Jazz & Afrikaans', hint: 'Miriam Makeba, Hugh Masekela' },
  { name: 'Şili', flag: '🇨🇱', tag: 'Nueva Canción', hint: 'Víctor Jara, Violeta Parra' },
]

// YouTube playlist — Dünya Seçkileri
const PLAYLIST_URL = 'https://www.youtube.com/playlist?list=PL2EwDahV2j7QJ9JM-oooSBNwlrW61Ze3v'

/**
 * Yılın hangi gününde olduğumuza göre ülke seçer.
 * 30 ülke rotasyon, 30 günde bir aynı ülke döner.
 */
function getTodayCountry() {
  const now = new Date()
  const start = new Date(now.getFullYear(), 0, 0)
  const diff = now.getTime() - start.getTime()
  const dayOfYear = Math.floor(diff / (1000 * 60 * 60 * 24))
  return COUNTRIES[dayOfYear % COUNTRIES.length]
}

/** Viski saati başladı mı? (15:30 sonrası) */
function isWhiskyTime() {
  const now = new Date()
  const h = now.getHours()
  const m = now.getMinutes()
  return h > 15 || (h === 15 && m >= 30)
}

/** Kaç dakika/saat kaldı? */
function timeUntilWhisky() {
  const now = new Date()
  const target = new Date()
  target.setHours(15, 30, 0, 0)
  if (now > target) return null
  const diff = target.getTime() - now.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
  if (hours > 0) return `${hours} saat ${minutes} dakika`
  return `${minutes} dakika`
}

export function WhiskyHourCard() {
  const [country, setCountry] = useState(getTodayCountry())
  const [active, setActive] = useState(isWhiskyTime())
  const [remaining, setRemaining] = useState(timeUntilWhisky())

  useEffect(() => {
    // Her dakikada bir durumu güncelle
    const interval = setInterval(() => {
      setCountry(getTodayCountry())
      setActive(isWhiskyTime())
      setRemaining(timeUntilWhisky())
    }, 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="bg-gradient-to-br from-amber-900/20 to-amber-600/5 border border-amber-500/20 rounded-xl p-5 relative overflow-hidden">
      {/* Dekoratif arka plan */}
      <div className="absolute top-0 right-0 text-8xl opacity-5 select-none pointer-events-none">
        🥃
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-3 relative z-10">
        <div className="flex items-center gap-2">
          <GlassWater className="w-5 h-5 text-amber-400" />
          <h3 className="font-bold text-slate-100">Viski Saati</h3>
        </div>
        {active ? (
          <span className="text-xs bg-amber-500/20 text-amber-300 px-2 py-1 rounded-full border border-amber-500/30">
            🟢 Başladı
          </span>
        ) : (
          <span className="text-xs bg-slate-700/50 text-slate-400 px-2 py-1 rounded-full flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {remaining} kaldı
          </span>
        )}
      </div>

      {/* Bugünün ülkesi */}
      <div className="mb-4 relative z-10">
        <div className="text-xs text-slate-500 mb-1">Bugünün durağı</div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl">{country.flag}</span>
          <span className="text-xl font-bold text-slate-100">{country.name}</span>
        </div>
        <div className="text-sm text-amber-300/80 mt-1">{country.tag}</div>
      </div>

      {/* Öneri sanatçılar */}
      <div className="mb-4 relative z-10">
        <div className="text-xs text-slate-500 mb-1 flex items-center gap-1">
          <Music className="w-3 h-3" />
          Bu akşam kulağa gelecek
        </div>
        <div className="text-sm text-slate-300 italic">{country.hint}</div>
      </div>

      {/* Mesaj */}
      <div className="mb-4 relative z-10">
        {active ? (
          <div className="text-sm text-amber-200">
            🥃 Kadehler kalksın Mustafa. Bir parmak yeter, tadını çıkar.
          </div>
        ) : (
          <div className="text-sm text-slate-400">
            Sabır. Saat 15:30'da başlayacak. O ana kadar işimize bakalım.
          </div>
        )}
      </div>

      {/* Playlist linki */}
      <a
        href={PLAYLIST_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 text-sm bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 px-3 py-2 rounded-lg transition relative z-10"
      >
        <Music className="w-4 h-4" />
        Playlist'i aç
        <ExternalLink className="w-3 h-3" />
      </a>
    </div>
  )
}
