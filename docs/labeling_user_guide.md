# KSÜ Bilgisayar Mühendisliği Bitirme Projesi
# İnsan Denetimli Patent İlgililik Etiketleme Kullanıcı Rehberi (PAT-0410 Hazırlık)

Bu rehber, araştırmacı ve denetçilerin **Patent İlgililik Etiketleme Aracını (`tools/labeling_app.py`)** güvenle, veri kaybı yaşamadan ve akademik standartlara uygun şekilde kullanabilmeleri için hazırlanmıştır.

---

## 1. Etiketleme Ekranı Nasıl Açılır?
Uygulama yerel Streamlit motoru üzerinde çalışır. Terminalde sanal ortam aktifken Streamlit komutu çalıştırılarak tarayıcıda açılır:
```powershell
.\.venv\Scripts\python.exe -m streamlit run tools/labeling_app.py
```
Komut çalıştırıldıktan sonra varsayılan tarayıcınızda otomatik olarak `http://localhost:8501` (veya uygun yerel port) adresi açılacaktır.

## 2. Hangi Klasörde Komut Çalıştırılır?
Komut her zaman projenin ana kök dizininde çalıştırılmalıdır:
```powershell
cd C:\Users\mehme\Desktop\Patent_Bitirm
```
Farklı bir alt klasörde çalıştırıldığında göreceli veri ve model yolları bulunamayabilir.

## 3. Sorgu ve Patent Nasıl Okunur?
Ekran iki ana inceleme kartına bölünmüştür:
- **Sol Kart (Teknik Sorgu ve Arama Çıkarımı):**
  - **Sorgu Metni:** İncelenen teknik problem veya kavram (Örn: `soil moisture sensor`).
  - **Teknik Odak:** Sorgunun temsil ettiği mühendislik alanı.
  - **BM25 Metrikleri:** Birinci aşama arama motorunun ürettiği ham leksikal skor, sıralama ve adaylık durumu (`Aday` veya `Aday Değil / Skor 0.0`).
  - **Grup ve Aile:** Patentin devam ailesi ve çapraz doğrulamada ait olduğu bağımsız değerlendirme grubu.
- **Sağ Kart (Patent Kaydı ve Kanıt Pasajı):**
  - **Patent Başlığı ve Numarası:** Resmi patent bibliyografyası.
  - **Başvuru No, Mucitler ve Hak Sahibi:** Patentin yasal kimlik bilgileri.
  - **Resmi Patent Özeti (Abstract):** Patentin resmi özet metni.
  - **En Yüksek Skorlu Kanıt Pasajı:** BM25 tarafından sorguyla en çok eşleşen metin bloğu (expander içinde bölüm ve iç konum bilgisiyle tam metin olarak sunulur). Eğer skor 0.0000 ise bu alanda kanıt bulunmadığı bilgisi verilir.

## 4. Patent Kaynağına Nasıl Gidilir?
Sağ kartın en üstünde yer alan patent numarası (Örn: `[US11674944B2]`), doğrudan Google Patents resmi veritabanındaki orijinal tescil sayfasına köprü bağlantılıdır. Tıklayarak patentin tam metnine, teknik çizimlerine ve bağımsız istemlerine (claims) yeni sekmede ulaşabilirsiniz.

## 5. "0 — İLGİSİZ" Etiketi Hangi Durumda Verilir?
- **Kriter:** Patent ile sorgu arasındaki teknik problem, temel çözüm mekanizması veya buluş sahası belirgin şekilde farklıysa.
- **Örnek:** Sorgu "toprak nem sensörü" iken patentin sadece genel bir radyo anteni yapısını anlatması veya kimyasal bir gübre bileşimi olması durumunda `0` verilir.

## 6. "1 — KISMEN İLGİLİ" Etiketi Hangi Durumda Verilir?
- **Kriter:** Patent genel uygulama alanı veya teknik çevre bakımından sorguyla benzerlik gösteriyor; ancak sorgunun aradığı spesifik çözüm mekanizması veya ana odak noktası patentin ana buluş konusuyla doğrudan örtüşmüyorsa (ikincil/yan özellik olarak geçiyorsa).
- **Örnek:** Sorgu "kablosuz sulama kontrolörü" iken patentin akıllı bir vana mekanizması anlatması ve telsiz iletişimden yalnızca yardımcı bir seçenek olarak bahsetmesi.

## 7. "2 — DOĞRUDAN İLGİLİ" Etiketi Hangi Durumda Verilir?
- **Kriter:** Patentin çözdüğü teknik problem, temel buluş konusu ve uyguladığı mekanizma doğrudan sorguyla birebir veya çok yakın örtüşüyorsa.
- **Örnek:** Sorgu "toprak nem sensörü" iken patentin doğrudan toprağa yerleştirilen kablosuz nem algılama probu ve elektrot mimarisini anlatması.

## 8. Etiket Nasıl Kaydedilir?
1. Sol kenar çubuğundaki "Denetçi Adı / Kimliği" alanına rumuzunuzu veya araştırmacı adınızı giriniz.
2. 3 seçenekli radyo düğmesinden (`0`, `1` veya `2`) uygun ilgililik kararını seçiniz.
3. İsteğe bağlı olarak "İnceleme Notu" kutusuna teknik gerekçenizi yazınız.
4. Mavi renkli **`💾 Etiketi Kaydet`** butonuna basınız.
5. Sistem etiketi atomik olarak diske yazar, yeşil onay bildirimi gösterir ve otomatik olarak bir sonraki kayda ilerler.

## 9. Önceki Etikete Nasıl Dönülür?
Bir önceki kaydı incelemek veya geriye dönük kontrol yapmak için ekranın altındaki **`⬅️ Önceki Kayıt`** butonuna tıklayınız.

## 10. Kaydedilmiş Etiket Nasıl Değiştirilir?
1. Değiştirmek istediğiniz kayda gidiniz (`⬅️ Önceki Kayıt` butonuyla veya sol kenar çubuğundaki filtreleri kullanarak).
2. Kartın sağ üstünde `DURUM: İNCELENDİ (Etiket: X)` ibaresi ve mevcut seçiminiz görüntülenecektir.
3. Radyo düğmesinden yeni etiketi seçiniz (veya notu güncelleyiniz).
4. **`💾 Etiketi Kaydet`** butonuna basınız. Dosyadaki etiket anında güncellenecektir.

## 11. Program Kapatılıp Açılınca Etiketler Korunur mu?
**EVET, %100 KORUNUR.** Tüm etiketler butona basıldığı anda diskteki `data/annotations/labeling_queue.csv` dosyasına atomik takas (`os.replace`) ve işletim sistemi önbellek temizleme (`os.fsync`) yöntemleriyle kalıcı olarak yazılır. Tarayıcıyı kapatsanız, bilgisayarı yeniden başlatsanız dahi verileriniz korunur. Yeniden açtığınızda kaldığınız yerden devam edebilirsiniz.

## 12. Etiketleme İlerlemesi Nerede Görünür?
Ekranın en üstünde 4 adet metrik kartı ve canlı ilerleme çubuğu yer alır:
- **Toplam Çift:** 160
- **İncelenen:** Kaydettiğiniz toplam etiket sayısı
- **Bekleyen:** Henüz etiketlenmemiş kalan çift sayısı
- **Tamamlanma:** Yüzdesel ilerleme oranı (Örn: `%12.5`)
Ayrıca sol kenar çubuğunda anlık etiket dağılımı (Kaç adet 0, kaç adet 1, kaç adet 2 verildiği) gerçek zamanlı güncellenir.

## 13. Yanlışlıkla Kaydetme veya İptal Durumunda Ne Yapılır?
Bir çifti yanlışlıkla etiketlediyseniz veya o kaydı yeniden "Bekliyor" durumuna almak istiyorsanız:
1. İlgili kaydı ekrana getiriniz.
2. Kırmızımsı gri renkli **`🗑️ Etiketi Sıfırla`** butonuna tıklayınız.
3. Kayıt anında `PENDING_HUMAN_REVIEW` durumuna dönecek, etiketi silinecek ve ilerleme sayacından düşülecektir.

## 14. Tüm Etiketler Nerede Tutulur?
Tüm etiketleme verileri yerel ve güvenli olarak projenin şu dosyasında saklanır:
`data/annotations/labeling_queue.csv`
Bu dosya UTF-8 formatında standart bir CSV dosyasıdır. Harici hiçbir bulut servisine, uzaktaki sunucuya veya üçüncü taraf API'ye veri gönderilmez.

