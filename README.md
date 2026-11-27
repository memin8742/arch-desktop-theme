# Arch Desktop Theme

Koyu lacivert Arch masaüstü; üst görev çubuğu, Zsh terminali, Thunar, açılış ve kilit ekranı için onaylı tasarım ve kurulum tanımları.

**v1.1.0: Xfce için kurulum aracı / deneme sürümü.** Codex olmadan kurulabilen bir araç eklendi. Hedef, mevcut **Arch Linux + Xfce + X11** oturumudur; işletim sistemi yükleyicisi değildir. Onaylı tasarım `paket/`, çalıştırılabilir kurulum kaynağı `installer/` içindedir.

![Terminal ve Thunar masaüstü önizlemesi](paket/02-onayli-masaustu.png)

## Codex kullanmadan kurulum

[v1.1.0 ZIP paketini indirin](https://github.com/memin8742/arch-desktop-theme/releases/tag/v1.1.0), bir klasöre çıkartın. `kur.sh` dosyasının bulunduğu klasörde sağ tıklayıp **Burada Terminal Aç** seçin:

```sh
bash kur.sh
```

Türkçe menüden **1 Kur / güncelle** seçin. Araç önce kapsamı gösterir; değişen dosya ve Xfce ayarlarını yedekler. Gereken resmi Arch paketleri, sistem güncellemesiyle birlikte kurulur. Parola yalnız `sudo` tarafından istenir; aracın tamamını `sudo` ile açmayın. Sonunda oturumu kapatıp tekrar açın.

Aynı menüden kontrol, **yedeğe dönme** ve yalnız tema ayarlarını dışa aktarma yapılır. [Kısa kullanım rehberi](KOLAY-KURULUM.txt).

```sh
bash kur.sh --plan   # Değişiklik yapmadan kapsam
bash kur.sh --check  # Kurulan bileşenlerin kontrolü
```

**Kapsam:** Duvar kâğıdı, Xfwm mavi çerçeve, üst panel, simgeli pencere düğmeleri, %80 zeminli Thunar, gerçek VTE/Zsh terminali, Fira Code, %80 terminal zemini, sekme/bölme/çıktı arama, kopyalama ve pano uygulanır. Mevcut panel eklentileri korunur; bu sürüm eksik özel eklentileri otomatik eklemez.

**Henüz otomatik uygulanmayanlar:** Birebir açılış/giriş/kilit tasarımı, batarya modları, özel CPU/MEM/NET kartları, ekran kaydı, tek Başlat ile menü ve pasif ışığın ayrıca azaltılması. Shift seçimi Zsh komut satırını kapsar; eski çıktı fareyle seçilir. Kurulum bunları bitmiş gibi göstermez. Onaylı istekler/görseller korunur; gerçek bilgisayarda görsel, ölçek, kilit ve donanım kabulü gerekir.

## Codex ile kurulum / kalan ayrıntılar

[Codex'e verilecek hazır isteği](CODEXE-VERILECEK-ISTEK.txt) kopyalayın. İstek repo bağlantısını da içerir; Codex'ten repoyu bilgisayara çekmesini ve kurulumu uygulamasını ister.

Kendiniz indirmek isterseniz:

```sh
git clone https://github.com/memin8742/arch-desktop-theme.git
cd arch-desktop-theme
python3 tools/package.py check
```

Xfce/X11 için önce `bash kur.sh` aracını kullanın. Codex'ten kalan ayrıntıları tamamlamasını isteyecekseniz [`KURULUM.md`](KURULUM.md) ve `paket/` içindeki tanımları verin. Araçta uygulanmış özelliklerle bekleyen tasarım isteklerini ayırın.

## Tasarım ve özellikler

- Terminal ve Thunar: mevcut koyu lacivert zemin, **%80 zemin opaklığı**, tam opak yazı/simgeler ve son seçilen Thunar görselindeki doygun mavi ince dış kontur ve dar/yumuşak, eşit ışık.
- Etkin pencere Thunar gibi ince mavi çerçeve, diğer pencereler aynı çerçeveyi yalnız yaklaşık %10 daha soluk kullanır; vurgu gerçek klavye odağıyla yer değiştirir ve panelde ilgili uygulama simgesiyle eşleşir.
- Terminal: Fira Code 10 pt, Zsh, iki satırlı dinamik dizin istemi, Kali temelli yazı/çıktı renkleri, geçmiş önerileri ve arama. İnce, yarı saydam, **üçgensiz** bölücüler ve bağımsız bölümler.
- Üst panel: Thunar çerçevesi gibi ince, kesintisiz tek mavi `#0AA6F0` alt çizgi ve aynı mavi eğimli uçlar; hafif/eşit ışık, beyaz kenar parlaması yok. Açık uygulamalar yalnız kendi simgeleriyle gösterilir, isim/başlık/yol yazılmaz. Dört çalışma alanı, pano geçmişi, bildirimler ve açılır sistem/batarya kutuları korunur. Donanım verileri gerçek ölçülür.
- Onaylı kısayollar, seçim/kopyalama/yapıştırma davranışları, ekran görüntüsü/kaydı, tema dışa aktarma ve uzun işlem bildirimi.
- Donanım destekliyorsa Ev şarj sınırları %55/%80, Seyahat geçici %100. Açılış, giriş ve gerçek oturum kilidi korunur.

Kesin fontlar, renkler, bütün **27 kısayol**, işlevler ve kabul kontrolleri [`04-ayarlar-ve-ozellikler.json`](paket/04-ayarlar-ve-ozellikler.json) içindedir. Görseller tasarım önizlemesidir; içlerindeki örnek komutlar kurulum talimatı sayılmaz.

## Güncelleme ve sürümler

Onaylı değişiklikler aynı repoya commit olarak gönderilir. Güncel bilgisayarda:

```sh
git pull --ff-only
python3 tools/package.py check
```

Ardından `bash kur.sh` menüsünden **Kur / güncelle** seçin. Dosyaları çekmek tek başına masaüstü ayarlarını değiştirmez. Her uygulama ayrı bir yedek oluşturur. Yedeğe dönüşte sonradan elle değişen dosyalar korunup raporlanır; kurulan dağıtım paketleri otomatik kaldırılmaz.

[Yayımlanmış sürümler ve ZIP paketleri](https://github.com/memin8742/arch-desktop-theme/releases) · [Değişiklikler](CHANGELOG.md) · [Kurulum ayrıntıları](KURULUM.md)

Kaynak doğrulama ve ZIP üretimi yalnız Python standart kütüphanesini kullanır:

```sh
python3 tools/package.py check
python3 tools/package.py build
```

Yeni içerik/sürüm hazırlanırken önce `VERSION` ve tanımlar güncellenir; ardından `python3 tools/package.py sync` özetleri yeniler. ZIP ve SHA256 dosyası `dist/` altında üretilir, Git geçmişine eklenmez. Videolar ve eski alternatif tasarımlar bu repoya alınmaz.

## Uygulama kaynakları

Çerçeveler [Xfwm'ın yerel XPM tema yapısını](https://wiki.xfce.org/howto/xfwm4_theme), panel [Xfce pencere düğmelerini](https://docs.xfce.org/xfce/xfce4-panel/tasklist) kullanır. Terminal PTY ve güvenli yapıştırma için [VTE](https://gnome.pages.gitlab.gnome.org/vte/gtk3/method.Terminal.paste_text.html), düzenlenen komutun seçimi için [Zsh ZLE](https://zsh.sourceforge.io/Doc/Release/Zsh-Line-Editor.html), ışık için [Picom](https://picom.app/) kullanır. Tüm pencereyi soldurarak saydamlık taklidi yapılmaz.
