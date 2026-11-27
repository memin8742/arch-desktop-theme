# Arch Desktop Theme

Koyu lacivert Arch masaüstü; üst görev çubuğu, Zsh terminali, Thunar, açılış ve kilit ekranı için onaylı tasarım ve kurulum tanımları.

**v1.2.5** mevcut **Arch Linux + Xfce + X11** oturumuna Arch Blue temasını kurar. Görsel kaynaklar `paket/`, kurulum kaynağı `installer/` dizinindedir.

![Terminal ve Thunar masaüstü önizlemesi](paket/02-onayli-masaustu.png)

## Kurulum

```sh
git clone https://github.com/memin8742/arch-desktop-theme.git
cd arch-desktop-theme
bash kur.sh
```

- **1 Kur / güncelle** masaüstünü, numaralı çalışma alanları ve simgeli görev listesini, terminali, Thunar'ı, ekran kaydını ve kilit stilini kurar. Gereken resmi paketler `pacman -Syu` ile kurulur.
- **5 Açılış, giriş ve root terminali** root kabuğundaki Shift+ok seçimini ve desteklenen systemd-boot makinelerde Plymouth ile LightDM temalarını yönetir. Root profili ayrıca seçilebilir.
- **2 Kontrol et**, **3 Yedeğe dön** ve **4 Tema ayarlarını dışa aktar** aynı menüdedir. Yeni GTK ayarları için masaüstü oturumunu kapatıp açın.

```sh
bash kur.sh --plan
bash kur.sh --check
```

[Sistem gereksinimleri ve geri dönüş](KURULUM.md) · [Kısa rehber](KOLAY-KURULUM.txt) · [Codex ile uygulama](CODEXE-VERILECEK-ISTEK.txt)

Üst panel ve Thunar araç çubuğu Arch Blue simgelerini kullanır. Ekran Kaydı Arch menüsünden açılır ve kayıt sırasında panel göstergesi belirir. Pil şarj modları kurulum kapsamı dışındadır. Shift+ok ile seçim düzenlenen Zsh komut satırında çalışır. Önceki terminal çıktısını fareyle seçebilirsiniz.

`Super+↓` pencereyi küçültür ve `Super+↑` aynı çalışma alanında bu şekilde küçültülen son pencereyi eski boyutuna getirir. Geri getirilecek pencere yoksa `Super+↑` odaktaki uygulamayı büyütür.

## Tasarım ve özellikler

- Terminalde lacivert zemin **%90 opak**, Thunar'da **%80 opak**. İkisinde de açık mavi oval kontur, yumuşak kenar ışığı ve tam opak yazı ve simgeler bulunur.
- Etkin pencere Thunar gibi ince mavi çerçeve, diğer pencereler aynı çerçeveyi yalnız yaklaşık %10 daha soluk kullanır; vurgu gerçek klavye odağıyla yer değiştirir ve panelde ilgili uygulama simgesiyle eşleşir.
- Terminal: Fira Code 10 pt, Zsh, iki satırlı dinamik dizin istemi, Kali temelli yazı/çıktı renkleri, geçmiş önerileri ve arama. İnce, yarı saydam, **üçgensiz** bölücüler ve bağımsız bölümler.
- Üst panelin alt çizgisi ve eğimli uçları ince `#0AA6F0` konturla birleşir. Açık uygulamalar yalnız kendi simgeleriyle gösterilir. Dört çalışma alanı, pano geçmişi, bildirimler ve açılır sistem/batarya kutuları bulunur. Donanım verileri gerçek ölçülür.
- Onaylı kısayollar, seçim/kopyalama/yapıştırma davranışları, ekran görüntüsü/kaydı, tema dışa aktarma ve uzun işlem bildirimi.
- Donanım destekliyorsa Ev şarj sınırları %55/%80, Seyahat geçici %100. Açılış, giriş ve gerçek oturum kilidi korunur.

Kesin fontlar, renkler, bütün **29 kısayol**, işlevler ve kabul kontrolleri [`04-ayarlar-ve-ozellikler.json`](paket/04-ayarlar-ve-ozellikler.json) içindedir. `Ctrl+Shift+R` yan yana, `Ctrl+Shift+E` veya `Ctrl+Shift+D` üst üste böler. `Ctrl+Shift+ok` komşu bölmeye geçer ve `Ctrl+Shift+B` son bölmeyi kapatır. Güncellemeden sonra yeni terminal pencerelerinde yeni kısayollar kullanılabilir.

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
