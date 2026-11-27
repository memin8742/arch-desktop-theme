# Arch / Xfce kurulumu

Repo: https://github.com/memin8742/arch-desktop-theme

Hazır kullanıcı isteği: [`CODEXE-VERILECEK-ISTEK.txt`](CODEXE-VERILECEK-ISTEK.txt).

## Kurulum menüsü

Arch Linux içinde Xfce/X11 oturumu açın. Repo dizininde `bash kur.sh` çalıştırıp **1 Kur / güncelle** seçin. Kurulum değişecek dosyaları ve Xfconf ayarlarını yedekler. Paket gerekiyorsa Arch paket yöneticisi sudo parolasını ister. Bir sonraki oturumda panel, Whisker Menu, Thunar, Picom ve CopyQ kullanıcı ayarlarından açılır.

**5 Açılış, giriş ve root terminali** sistem bileşenlerini yönetir.

- **1** Arch Terminal'deki etkileşimli root oturumuna Zsh seçim profilini ekler. Root Bash'in hesap kabuğu olarak kaydı korunur. Aracın root profili, root mülkiyetindeki dosyalardan yüklenir. Açık root kabuğundan `exit` ile çıkıp `sudo -i` ile tekrar girin.
- **2** EFI, `/boot`, systemd-boot ve systemd tabanlı standart `linux` initramfs üzerinde ayrı bir Plymouth girdisi üretir. LightDM GTK Greeter varsa ona Arch Blue stilini uygular. Arch Blue girdisi bir sonraki açılışta menüden denenebilir.
- **3** Arch Blue girdisini varsayılan yapar ve LightDM'de açılışta parola ekranını gösterir. Standart **Arch Linux** girdisi erişilebilir kalır. Plymouth imajı ilgili paket güncellemelerinde yenilenir.
- **4** `/var/backups/arch-desktop-theme` altındaki tarihli sistem yedeğiyle bu adımları geri alır. Kullanıcı temasının yedeği ana menüde **3 Yedeğe dön** seçeneğindedir.

Xfce'nin yerel bileşenleri ve monitör ölçeği son görünümü etkiler. Sistem menüsü yeniden başlatmayı kullanıcıya bırakır.

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
- Üst panelin alt çizgisi ve eğimli uçları Thunarın ince mavi çerçevesi gibi aynı tek renk `#0AA6F0` ve hafif/eşit ışıklı olsun; aqua/yeşil kayma, kesinti, beyaz/gümüş uç veya aşırı parlama ekleme. Orta bölümde açık uygulamalar yalnız kendi logolarını gösterir; uygulama adı, pencere başlığı veya dizin yolu yazılmaz. Adlar fareyle üzerine gelince ipucunda gösterilir; odak/alta alma/geri getirme ve çoklu pencere erişimi korunur.
- Panel alt çizgisi/uçları `tek_parca_kontur` gibi aynı yoldan çizilir. Özellikle sağ üst eğimli ucun üst noktasında ve yatay çizgiyle birleşiminde kesinti, çentik, farklı ton veya clip hatası olmadığını farklı ölçeklerde kontrol et.
- Terminal dışı `03`, ince ve üçgensiz bölücüler `07/08`, dosya/log ve istem renkleri `08/09`. Fira Code 10 pt ve JSON'daki kesin RGB değerleri uygulanır.
- Terminal ve Thunar zeminleri %80 opak; metin/simge/grafikler tam opak. Genel pencere soldurması veya içerikte sabit logo resmiyle taklit yok. Dış kontur tonu/ışığı `11`deki son seçilmiş doygun mavi ve dar/yumuşak hale gibi; tüm kenar/köşelerde eşit. `ortak_pencere_stili.dis_kontur_ve_hale` uygulanır. Önceden onaylı istem/çıktı ve iç bölücü renklerini bu düzeltmeyle değiştirme.
- `ortak_pencere_stili.odak_vurgusu`: etkin pencere Thunar referansı gibi ince mavi çerçeveli, pasifler aynı yapı ve tonda yalnız yaklaşık %10 daha soluktur; kalın etkin veya çok koyu pasif kontur oluşturma. Tıklama/Alt+Tab/panel/çalışma alanı/modal değişiminde vurgu doğru pencereye ve yalnız ilgili uygulama simgesine geçer. Metin/ikon/içerik opaklığını bununla değiştirme; eşit ışığı her pencerenin kendi çevresinde koru.
- Thunar `11` gibi gerçek dosyalarla çalışır. Açılış ve giriş/kilit `05/06`; batarya kutusu `10`.
- Bütün 27 kısayol, bölmeler/sekmeler, geçmiş/arama, Windows benzeri seçim, pano, bildirim/kayıt/dışa aktarma işlevleri uygulanır.
- Sistem sensörleri/VRAM ve şarj eşikleri gerçek donanım yetenekleriyle doğrulanır; desteklenmeyen özellik için sahte başarı gösterilmez.

## Kontrol ve teslim

JSON'daki kabul kontrollerini gerçek oturumda uygula: pencere işlemleri, tüm kısayollar, terminal bölümleri, seçim/pano/arama, Thunar dosya işlemleri, kilit, panel, donanım değerleri, kayıt ve dışa aktarma.

Sonunda Türkçe olarak yapılan değişiklikleri, test sonuçlarını, varsa uygulanamayan ayrıntıları ve yedeğe dönüş yolunu bildir. Kurulum testleri Windows üzerinde yapılmış gibi gösterilmez; görseller gerçek Arch kurulumunun kanıtı değildir.

Sonraki güncellemelerde aynı repo güncellenir ve yalnız değişen tanımlar mevcut sisteme birleştirilir. Kişisel komut/pano geçmişi, parolalar ve kullanıcı dosyaları GitHub'a gönderilmez.
