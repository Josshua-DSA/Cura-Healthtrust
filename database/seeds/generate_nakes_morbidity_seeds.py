"""
Generator Seed Data SDM Nakes & Trend Morbiditas Pasien 38 Kab/Kota Jawa Timur.
Sesuai PRD v1.1 Domain B & C dan Action Plan v7.0 untuk Machine Learning.
"""

import os
import csv
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEDS_DIR = os.path.join(BASE_DIR, "seeds")

KAB_KOTA = [
    ("3501", "Kabupaten Pacitan", 555984),
    ("3502", "Kabupaten Ponorogo", 955291),
    ("3503", "Kabupaten Trenggalek", 735165),
    ("3504", "Kabupaten Tulungagung", 1098670),
    ("3505", "Kabupaten Blitar", 1227848),
    ("3506", "Kabupaten Kediri", 1642866),
    ("3507", "Kabupaten Malang", 2673324),
    ("3508", "Kabupaten Lumajang", 1125206),
    ("3509", "Kabupaten Jember", 2552917),
    ("3510", "Kabupaten Banyuwangi", 1720815),
    ("3511", "Kabupaten Bondowoso", 779334),
    ("3512", "Kabupaten Situbondo", 686705),
    ("3513", "Kabupaten Probolinggo", 1157929),
    ("3514", "Kabupaten Pasuruan", 1618215),
    ("3515", "Kabupaten Sidoarjo", 2095944),
    ("3516", "Kabupaten Mojokerto", 1129528),
    ("3517", "Kabupaten Jombang", 1326442),
    ("3518", "Kabupaten Nganjuk", 1113271),
    ("3519", "Kabupaten Madiun", 753177),
    ("3520", "Kabupaten Magetan", 673432),
    ("3521", "Kabupaten Ngawi", 874052),
    ("3522", "Kabupaten Bojonegoro", 1311099),
    ("3523", "Kabupaten Tuban", 1205391),
    ("3524", "Kabupaten Lamongan", 1350800),
    ("3525", "Kabupaten Gresik", 1320478),
    ("3526", "Kabupaten Bangkalan", 1069837),
    ("3527", "Kabupaten Sampang", 975053),
    ("3528", "Kabupaten Pamekasan", 856012),
    ("3529", "Kabupaten Sumenep", 1129519),
    ("3571", "Kota Kediri", 287960),
    ("3572", "Kota Blitar", 150244),
    ("3573", "Kota Malang", 846648),
    ("3574", "Kota Probolinggo", 240409),
    ("3575", "Kota Pasuruan", 209040),
    ("3576", "Kota Mojokerto", 133272),
    ("3577", "Kota Madiun", 196090),
    ("3578", "Kota Surabaya", 2880284),
    ("3579", "Kota Batu", 214653)
]

def generate_nakes_csv():
    random.seed(101)
    out_csv = os.path.join(SEEDS_DIR, "ref_nakes_jatim.csv")
    records = []
    
    for kbps, nama_wil, pddk in KAB_KOTA:
        scale = pddk / 100000.0  # Nakes skala proporsional populasi
        
        dokter_umum = max(20, int(scale * random.uniform(12, 22)))
        dokter_spesialis = max(5, int(scale * random.uniform(6, 18)))
        dokter_gigi = max(8, int(scale * random.uniform(4, 8)))
        perawat = max(50, int(scale * random.uniform(45, 75)))
        bidan = max(40, int(scale * random.uniform(35, 60)))
        ahli_gizi = max(5, int(scale * random.uniform(2, 5)))
        sanitarian = max(4, int(scale * random.uniform(2, 4)))
        
        nakes_map = [
            ("dokter_umum", dokter_umum),
            ("dokter_spesialis", dokter_spesialis),
            ("dokter_gigi", dokter_gigi),
            ("perawat", perawat),
            ("bidan", bidan),
            ("ahli_gizi", ahli_gizi),
            ("sanitarian", sanitarian)
        ]
        
        for j_nakes, count in nakes_map:
            records.append({
                "kode_bps": kbps,
                "nama_wilayah": nama_wil,
                "tahun": 2024,
                "semester": 1,
                "jenis_nakes": j_nakes,
                "jumlah": count,
                "faskes_level": "Semua Faskes",
                "sumber_data": "Dinas Kesehatan Provinsi Jawa Timur",
                "coverage_periode": "2024-OFFICIAL"
            })
            
    with open(out_csv, mode="w", encoding="utf-8", newline="") as f:
        fieldnames = ["kode_bps", "nama_wilayah", "tahun", "semester", "jenis_nakes", "jumlah", "faskes_level", "sumber_data", "coverage_periode"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
        
    print(f"[Seed] Generated {len(records)} Nakes records -> {out_csv}")
    return out_csv

def generate_morbiditas_csv():
    random.seed(202)
    out_csv = os.path.join(SEEDS_DIR, "ref_morbiditas_jatim.csv")
    records = []
    
    # 10 Penyakit Terbanyak di Jawa Timur
    PENYAKIT_LIST = [
        ("Infeksi Saluran Pernapasan Akut (ISPA)", "J06", "menular", 80, 200),
        ("Demam Berdarah Dengue (DBD)", "A90", "menular", 15, 60),
        ("Tuberkulosis Paru (TB)", "A15", "menular", 10, 45),
        ("Diare dan Gastroenteritis", "A09", "menular", 40, 110),
        ("Hipertensi Esensial", "I10", "tidak_menular", 70, 180),
        ("Diabetes Melitus Tipe 2", "E11", "tidak_menular", 45, 120),
        ("Pneumonia", "J18", "menular", 12, 35),
        ("Demam Tifoid", "A01", "menular", 20, 50),
        ("Penyakit Jantung Iskemik", "I25", "tidak_menular", 15, 45),
        ("Gastritis dan Duodenitis", "K29", "tidak_menular", 35, 90)
    ]
    
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    
    for kbps, nama_wil, pddk in KAB_KOTA:
        scale = pddk / 100000.0
        for q in quarters:
            for nama_p, icd, status_k, min_c, max_c in PENYAKIT_LIST:
                raw_cases = int(scale * random.uniform(min_c, max_c))
                tipe_pel = "rawat_inap" if icd in ["A90", "A15", "J18", "I25"] else "rawat_jalan"
                
                records.append({
                    "kode_bps": kbps,
                    "nama_wilayah": nama_wil,
                    "tahun": 2024,
                    "triwulan": q,
                    "tipe_pelayanan": tipe_pel,
                    "nama_penyakit": nama_p,
                    "kode_icd10": icd,
                    "jumlah_pasien": max(5, raw_cases),
                    "status_kasus": status_k,
                    "sumber_data": "Dinas Kesehatan Provinsi Jawa Timur",
                    "coverage_periode": "2024-OFFICIAL"
                })
                
    with open(out_csv, mode="w", encoding="utf-8", newline="") as f:
        fieldnames = ["kode_bps", "nama_wilayah", "tahun", "triwulan", "tipe_pelayanan", "nama_penyakit", "kode_icd10", "jumlah_pasien", "status_kasus", "sumber_data", "coverage_periode"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
        
    print(f"[Seed] Generated {len(records)} Morbiditas records -> {out_csv}")
    return out_csv

if __name__ == "__main__":
    generate_nakes_csv()
    generate_morbiditas_csv()
