# v1.1.0 — Xfce kurulum aracı (deneme)

- Codex gerektirmeyen Türkçe kurulum/kontrol/geri dönüş/dışa aktarma menüsü ve kısa kullanıcı rehberi.
- Arch/Xfce/X11 denetimi; resmi paketler, değişiklik öncesi dosya ve xfconf yedeği; başarısız işlemde geri dönüş; sonradan düzenlenen dosyaları koruma.
- Duvar kâğıdı, yerel Xfwm XPM çerçeveleri, tek mavi SVG panel çizgisi, simgeli pencere düğmeleri ve koyu Thunar ayarları.
- Gerçek GTK/VTE terminal: %80 yalnız zemin alfa, Fira Code, Zsh renkli iki satır istem, bağımsız PTY bölmeleri, aynı dizinde sekme, geçmiş/çıktı araması, özel kopyalama/kesme ve ZLE komut seçimi.
- CopyQ metin/görsel geçmişi, gerçek sensör bilgisi, güvenli tema ayarları dışa aktarma. Önceki 27 kısayol ve tüm tasarım istekleri korunur; uygulanmamış ayrıntılar ayrı raporlanır.
- Tamamlanmamış kapsam README, kısa rehber ve kurulum raporunda açıkça gösterilir. Özellikle Thunar yalnız zemin alfa, birebir açılış/giriş/kilit, şarj modları ve diğer bekleyen özellikler bitmiş sayılmaz.
- Geçici Arch/Xfwm/Xvfb bütünleştirme kontrolü eklendi; fiziksel donanım testi yerine geçmez.

# Değişiklikler

## v1.0.4 — 2026-11-27

- Etkin pencere, seçilen Thunar referansındaki ince mavi çerçeve ve yumuşak ışığı kullanır; pasif pencere aynı yapı/tonda yalnız yaklaşık %10 daha soluktur. Kalın etkin ve çok koyu pasif çerçeve ayrımı kaldırıldı.
- Üst panelin bütün alt çizgisi ve eğimli uçları da Thunar çerçevesi gibi tek mavi `#0AA6F0` ve hafif/eşit ışık kullanır. Beyaz/gümüş uç veya bölgesel renk geçişi yok.
- Sağ üst panel ucunun tek konturla bağlanması ve farklı ölçeklerde kesinti/ton farkı kontrolü eklendi.
- Birlikte önizlemede Thunar etkin, terminal pasif örnektir; gerçek odakta roller değişir. %80 zemin, tam opak içerik ve önceki diğer özellikler korunur.

## v1.0.3 — 2026-11-27

- Gerçek klavye odağı olan pencere belirgin mavi çerçeve, pasif pencereler daha sakin kontur/ışık kullanır. Vurgu odakla yer değiştirir; içerik ve yazılar soldurulmaz.
- Panelde yalnız odaktaki uygulamanın simgesi/grubu belirginleşir. Bütün alt çizgi ve eğimli uçlar, kullanıcının okla seçtiği koyu mavi `#02258D` olarak tek renge sabitlendi.
- Birlikte masaüstü önizlemesi ve kurulum/kabul tarifleri güncellendi. Önceki 27 kısayol, %80 zemin, yazı/istem renkleri, iç bölücüler ve diğer işlevler korunur.

## v1.0.2 — 2026-11-27

- Terminal ve Thunar dış çerçeve rengi/ışığı, kullanıcının seçtiği Thunar referansına bağlandı: doygun mavi ince kontur, dar/yumuşak ve eşit mavi hale. Sayısal uygulama başlangıç değerleri ve karşılaştırma kapsamı eklendi.
- Birlikte masaüstü ve tek terminal önizlemeleri eşleştirildi; Thunarın seçilen çerçevesi korundu. 08/09 yalnız terminal içi renk/kullanım referansıdır.
- Tek terminal önizlemesinin üst panel kenarlarında kalan beyaz/gümüş çizgi parçaları da giderildi; güncel masaüstü/terminal/Thunar önizlemelerinde alt kontur denetlendi.
- %80 lacivert zemin, bütün yazı/istem renkleri, iç bölücüler, simgeli/parlamasız üst panel, 27 kısayol ve diğer işlevler korundu.

## v1.0.1 — 2026-11-27

- Üst görev çubuğunun alt çizgisi masaüstüne uyumlu tek renk mavi `#237DB5` olarak tanımlandı; aqua renk kaymaları ve uçlardaki beyaz parlamalar kaldırıldı.
- Açık uygulama düğmeleri yalnız simge kullanıyor; ad, pencere başlığı ve dizin yolu etiketleri kaldırıldı. Hover ipucu, odak/alta alma/geri getirme ve çoklu pencere erişimi korunuyor.
- Masaüstü, terminal ve Thunar önizlemeleri ile kurulum tarifleri eşleştirildi. Batarya kutusunun onaylı eşikleri, önceki 27 kısayol ve bütün diğer özellikler korundu.

## v1.0 — 2026-11-26

İlk GitHub yayını. Onaylı güncel masaüstü ve kurulum tanımları sabit `paket/` dizinine taşındı.

- Terminal ve Thunarda %80 zemin opaklığı; net yazı/simgeler, korunmuş lacivert renk ve eşit/hafif mavi çerçeve ışığı.
- İnce, yarı saydam ve üçgensiz terminal bölücüleri; Zsh/Fira Code ve onaylı istem/çıktı renkleri.
- Üst panel, açılış/giriş/kilit, 27 kısayol, geçmiş/arama/seçim/pano, kayıt, bildirim ve dışa aktarma tanımları.
- Gerçek sensör/VRAM değerleri ve donanıma bağlı Ev %55/%80, Seyahat geçici %100 şarj kuralları.
- Repo bağlantısından Codex ile kurulum/güncelleme yönergesi; paket doğrulama ve tekrar üretilebilir ZIP aracı.

Videolar ve önceki alternatif tasarımlar yayıma dahil edilmedi. Görseller referans önizlemeleridir; gerçek Arch kurulum testleri hedef bilgisayarda yapılır.
