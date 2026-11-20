# Makine Öğrenmesi ile Patent İlgililik Modeli Tasarımı (PAT-0401)

Bu doküman, Yapay Zekâ Destekli Patent Ön Araştırma Sistemi'nin 1. Katmanında yer alan ikinci aşama olan **Makine Öğrenmesi Tabanlı Yeniden Sıralama (ML Reranking)** modelinin matematiksel çerçevesini, problem tanımını, öznitelik mühendisliğini, veri sızıntısı önleme stratejisini ve bilimsel sınırlarını tanımlar.

---

## 1. Problem Tanımı ve İki Aşamalı Mimari (Two-Stage Retrieval)

Geniş patent veri tabanlarında doğrudan karmaşık makine öğrenmesi modelleri veya yoğun vektör karşılaştırmaları çalıştırmak hesaplama maliyeti ve gecikme açısından verimsizdir. Bu nedenle bilgi getiriminde endüstri standardı olan **iki aşamalı hiyerarşik mimari** benimsenmiştir:

```
[Kullanıcı Teknik Sorgusu (Q)]
               │
               ▼
┌────────────────────────────────────────────────────────┐
│ 1. AŞAMA: Birincil Bilgi Getirimi (Retriever)          │
│ Algoritma: BM25Okapi (Pasaj İndeksi + Max-Pooling)     │
│ Kapsam: Tüm korpus (256 pasaj / N patent)              │
│ Çıktı: İlk 20 Aday Patent (Top-20 Candidates)          │
└────────────────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────┐
│ 2. AŞAMA: Makine Öğrenmesi ile Yeniden Sıralama        │
│ Model: scikit-learn Logistic Regression                │
│ Girdi: (Sorgu Q, Aday Patent P) Öznitelik Vektörü x    │
│ Çıktı: İlgililik Olasılık Skoru P(Relevance = 1 | x)   │
│ Sıralama: Olasılık skoruna göre azalan sıralama        │
└────────────────────────────────────────────────────────┘
               │
               ▼
[Kullanıcı Sunumu: Kaynaklı En İlgili İlk 5 Patent (Top-5)]
```

---

## 2. Girdi ve Çıktı Tanımı

### Girdi
- **Sorgu ($Q$):** Kullanıcının buluş formundan türetilen İngilizce teknik terim kümesi.
- **Aday Patent ($P$):** BM25 aşamasında pozitif skor üreten ve ilk 20 aday arasına giren doğrulanmış patent kaydı.
- **Öznitelik Vektörü ($\vec{x} \in \mathbb{R}^d$):** Sorgu ile patent arasındaki çok boyutlu benzerlik ve yapısal sinyalleri temsil eden sayısal vektör.

### Çıktı
- **İlgililik Skoru ($\hat{y} \in [0, 1]$):** Modelin adayın teknik sorgu ile ilgili olma olasılığına verdiği tahmin.
- **Sıralanmış Liste:** İlk 20 aday içerisinden en yüksek olasılık skoruna sahip ilk 5 patentin seçilmesi.

> [!IMPORTANT]
> **Kritik İlke:** Modelin görevi "Bu buluş patentlenebilir mi?" veya "Yenilik ihlali var mı?" sorularına hukuki yanıt vermek DEĞİLDİR. Modelin yegâne görevi "Bu patent dokümanı kullanıcının teknik sorgusuyla ne kadar ilgilidir?" sorusuna istatistiksel bir sıralama üretmektir.

---

## 3. Seçilen Model Mimarisi: Neden Logistic Regression?

Başlangıç modeli olarak derin sinir ağları veya aşırı parametreli modeller yerine **scikit-learn Logistic Regression** seçilmiştir:

1. **Yorumlanabilirlik ve Şeffaflık:**
   - Her özniteliğin katsayısı ($\beta_i$), o özniteliğin ilgililik kararına etkisini açıkça gösterir (örneğin başlık eşleşmesinin mi yoksa BM25 pasaj skorunun mu daha belirleyici olduğu denetlenebilir).
2. **Küçük Örneklem Direnci (Low Sample-Size Robustness):**
   - Pilot aşamada veri boyutu sınırlıdır. Karmaşık ağlar (transformer, gradient boosting) küçük veri kümelerinde hızla ezberleme (overfitting) eğilimi gösterir. L2 regülarizasyonlu ($C$ parametreli) lojistik regresyon aşırı öğrenmeye karşı son derece dayanıklıdır.
3. **Düşük Gecikme ve Sıfır GPU İhtiyacı:**
   - 20 aday patent için öznitelik çıkarımı ve model tahmini standart bir CPU üzerinde milisaniyeler mertebesinde tamamlanır.

---

## 4. Öznitelik Mühendisliği (Feature Engineering)

Model, sorgu-patent çifti $(Q, P)$ için şu 7 bağımsız özniteliği hesaplar:

| No | Öznitelik Adı | Tip | Tanım ve Matematiksel Formülasyon |
|---|---|---|---|
| 1 | `bm25_patent_score` | Reel | Patentin max-pooled BM25 skoru (log normalizasyonlu: $\ln(1 + \text{score})$) |
| 2 | `title_token_overlap` | $[0, 1]$ | Sorgu tokenlarının patent başlığındaki örtüşme oranı: $\frac{\|Tokens(Q) \cap Tokens(Title)\|}{\|Tokens(Q)\|}$ |
| 3 | `abstract_token_overlap` | $[0, 1]$ | Sorgu tokenlarının resmi patent özetindeki örtüşme oranı: $\frac{\|Tokens(Q) \cap Tokens(Abstract)\|}{\|Tokens(Q)\|}$ |
| 4 | `best_passage_overlap` | $[0, 1]$ | Sorgu tokenlarının en yüksek skorlu kanıt pasajındaki örtüşme oranı |
| 5 | `cpc_domain_match` | Tamsayı | Patentin hedef teknik alan CPC kodları (A01G25, G01N) ile örtüşen sınıf sayısı |
| 6 | `best_section_is_abstract` | $\{0, 1\}$ | En iyi pasajın Özet bölümünden gelip gelmediğini belirten ikili bayrak |
| 7 | `doc_length_ratio` | Reel | Patent tarifname kelime sayısının korpus ortalama uzunluğuna oranı ($\frac{W_P}{\bar{W}}$) |

---

## 5. Veri Sızıntısını Önleme (Patent Family Grouping)

Makine öğrenmesinde en tehlikeli veri sızıntılarından (data leakage) biri, aynı patent ailesine (aynı buluşun devam veya öncelik başvurularına) ait dokümanların rastgele eğitim ve test kümelerine bölünmesidir.

### Çözüm Protokolü:
- Eğitim ve test ayrımı yapılırken `GroupKFold` veya aile düzeyinde tabakalı ayırma (`GroupShuffleSplit`) kullanılacaktır.
- Gruplama anahtarı: `family_id` (Örn. `FAM_US_IRR_WIRELESS_01` veya `FAM_US_DRESSELHAUS_SOIL_01`).
- Bir aileye ait tüm patentler (örneğin US7836910B2 ve US8671969B2) **kesinlikle ya sadece eğitim kümesinde ya da sadece test kümesinde** yer alacaktır. Asla bölünmeyecektir.

---

## 6. Bilimsel Değerlendirme Metrikleri

Etiketli veri kümesi tamamlandığında model başarımı şu akademik metriklerle ölçülecektir:
1. **Precision@5 (P@5):** İlk 5 sırada önerilen patentlerin kaçının ilgili olduğu.
2. **Mean Average Precision (MAP@5):** Sıralama kalitesini ödüllendiren ortalama kesinlik.
3. **Normalized Discounted Cumulative Gain (nDCG@5):** Kademeli ilgi düzeylerini (0, 1, 2) ve sıralama pozisyonunu logaritmik olarak cezalandıran standart metrik.
4. **Mean Reciprocal Rank (MRR):** İlk ilgili patentin önerildiği pozisyonun tersi ($1 / \text{rank}_1$).

---

## 7. Pilot Sınırları ve Bilimsel Dürüstlük

1. **Örneklem Sınırı:** Pilot korpus 8 patent içermektedir. Bu aşamada eğitilecek herhangi bir model istatistiksel genelleme gücüne sahip olamaz. Bu nedenle PAT-0301-D01 kapsamında model eğitimi YAPILMAYACAK; yalnızca etiketleme altyapısı ve veri şablonu hazırlanacaktır.
2. **Etiketleme Kaynağı:** Model başarımı uydurma veya sentetik etiketlerle hesaplanamaz; yalnızca PAT-0402 kurallarına göre insanlar tarafından doğrulanmış etiketlerle hesaplanabilir.

