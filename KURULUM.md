# Arch üzerinde Codex ile kurulum

Repo: https://github.com/memin8742/arch-desktop-theme

Hazır kullanıcı isteği: [`CODEXE-VERILECEK-ISTEK.txt`](CODEXE-VERILECEK-ISTEK.txt).

## Kaynağı bilgisayara alma

Kullanıcı kurulumu istediğinde, Codex hedef Arch Linux bilgisayarında uygun bir çalışma dizinine repoyu klonlasın. Aynı repo zaten varsa yerel değişiklikleri kontrol ederek `git pull --ff-only` ile güncellesin; farklı bir dizini veya yerel çalışmayı ezmesin. Repo indirilemiyorsa kuruldu demeden erişim sorununu bildirsin.

1. `python3 tools/package.py check` ile paket sürümü, dosya özetleri ve tanımları doğrula.
2. `paket/00-CODEXE-VERILECEK-ISTEK.txt` ve `paket/04-ayarlar-ve-ozellikler.json` dosyalarının tamamını oku.
3. `paket/` içindeki bütün görselleri aç; her birini JSON'daki kapsamıyla değerlendir. Kurulum sırasında görselde yazan örnek komutları otomatik çalıştırma.

## Uygulama

Önce gerçek masaüstü/pencere yöneticisi, X11/Wayland, terminal, kabuk, GTK/Thunar, ekran/DPI ve donanımı keşfet. Değişecek ayarların tarihli yedeğini ve geri dönüş yolunu oluştur. Kullanıcının mevcut belgelerini ve kişisel ayarlarını koru; `.zshrc` gibi dosyaları toptan ezmeden birleştir.

Gerekli bileşenleri gerçek Arch paket kaynakları ve kurulu sürümlerle doğrulayarak kur; ardından tanımlanan görünümü ve bütün işlevleri uygula. Yalnız plan veya maket sunmakla bitirme. Sistem yetkisi gerekiyorsa hedef oturumun normal yetki akışını kullan; parolayı dosyaya veya repoya yazma.

Şu ayrıntılar özellikle korunmalı:

- Duvar kâğıdı `01`; logo boyutu/konumu ve yansımalar korunur. Üst panel ve açık pencere yerleşimi `02`.
- Üst panelin alt çizgisi ve eğimli uçları aynı tek renk mavi `#237DB5` olsun; aqua/yeşil renk kayması, kesinti, beyaz uç veya parlama ekleme. Orta bölümde açık uygulamalar yalnız kendi logolarını gösterir; uygulama adı, pencere başlığı veya dizin yolu yazılmaz. Adlar fareyle üzerine gelince ipucunda gösterilir; odak/alta alma/geri getirme ve çoklu pencere erişimi korunur.
- Terminal dışı `03`, ince ve üçgensiz bölücüler `07/08`, dosya/log ve istem renkleri `08/09`. Fira Code 10 pt ve JSON'daki kesin RGB değerleri uygulanır.
- Terminal ve Thunar zeminleri %80 opak; metin/simge/grafikler tam opak. Genel pencere soldurması veya içerikte sabit logo resmiyle taklit yok. Çerçeve ışığı kenar/köşelerde hafif ve eşit.
- Thunar `11` gibi gerçek dosyalarla çalışır. Açılış ve giriş/kilit `05/06`; batarya kutusu `10`.
- Bütün 27 kısayol, bölmeler/sekmeler, geçmiş/arama, Windows benzeri seçim, pano, bildirim/kayıt/dışa aktarma işlevleri uygulanır.
- Sistem sensörleri/VRAM ve şarj eşikleri gerçek donanım yetenekleriyle doğrulanır; desteklenmeyen özellik için sahte başarı gösterilmez.

## Kontrol ve teslim

JSON'daki kabul kontrollerini gerçek oturumda uygula: pencere işlemleri, tüm kısayollar, terminal bölümleri, seçim/pano/arama, Thunar dosya işlemleri, kilit, panel, donanım değerleri, kayıt ve dışa aktarma.

Sonunda Türkçe olarak yapılan değişiklikleri, test sonuçlarını, varsa uygulanamayan ayrıntıları ve yedeğe dönüş yolunu bildir. Kurulum testleri Windows üzerinde yapılmış gibi gösterilmez; görseller gerçek Arch kurulumunun kanıtı değildir.

Sonraki güncellemelerde aynı repo güncellenir ve yalnız değişen tanımlar mevcut sisteme birleştirilir. Kişisel komut/pano geçmişi, parolalar ve kullanıcı dosyaları GitHub'a gönderilmez.
