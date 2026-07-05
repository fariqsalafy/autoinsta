"""Batch content generator for @kisahmu356

Niche: Konten untuk pemuda dengan sentuhan Sirah Nabi Muhammad SAW.
Output: Batch posting ke Content Hub (SQLite via app.py API).
"""
import os, json, random, requests

BASE = 'http://127.0.0.1:5000'
QUOTES = [
    ("Di tengah kota penuh berhala, Muhammad SAW tetap jujur hingga dapat gelar Al-Amin.", "Kisah Al-Amin", "Kejujuran itulah mata uang paling mahal di masyarakat. Sebelum nabi, dia sudah diburu karena integrity.", ["kejujuran","sirah","sahabat","pemuda","al-amin"]),
    ("Muhammad SAW pernah gembala kambing demi menafkahi diri sendiri.", "Gembala Kambing", "Kadar awal nabi bukanlah meja kantor, tapi padang gembala. Hidup sederhana menumbuhkan kehormatan.", ["sirah","nabi","gembala","kemampuan","pemuda"]),
    ("Hijrah bukan cuma pindah kota, tapi pindah pola pikir.", "Hijrah Makkah-Madinah", "Melangkah dari zona nyaman ke zona tak menentu hanya karena keyakinan: itulah true courage.", ["hijrah","keyakinan","courage","pemuda","sirah"]),
    ("Ketika orang tertawa karena mimpi buruk, Nabi terbangun dan bersujud.", "Ketakutan di Gua Hira", "Perasaan human biasa. Rasul juga merasa tak. Dia jawabnya dengan sholat, bukan drama.", ["sholat","gurahira","kumpul","pemuda","sirah"]),
    ("Jabatannya sebagai penghulu berakhir malah menambah kerendahan hati.", "Jabatan Rasul", "Semakin tinggi, semakin rendah. Power itu kayah gunung, tinggi tapi lebih rendah dari bumi.", ["kepemimpinan","rendahhati","sirah","pemuda","nabi"]),
    ("Kalau Muhammad SAW bisa baca langit dengan dadanya, kamu juga bisa baca isi hatimu.", "Identitas Rasul", "Mu lahir dari spesial? Engga. Doa + tawakal = akses langit.", ["doa","tawakal","sirah","pemuda"]),
    ("Bisnisnya dimulai dari perjalanan perdagangan ke Syam, diiringi kejujuran.", "Muhammad SAW sebagai Pedagang", "Dagang bukan cuma untung, tapi amanah. Barang dagangannya Cater kepercayaan.", ["dagang","bisnis","jujur","sirah","pemuda"]),
    ("Dia bantu orang tua, nyambung keluarga, jagain anak yatim.", "Pribadi Rasul", "Karakter sebelum kenai wahyu: Bethree to the max.", ["family","charakter","sirah","pemuda"]),
    ("Jangan Hanya nge-klik 'like', tapi nyatain kehidupan sebenarnya.", "Kontras Vita Modern vs Sirah", "Feed penuh highlight, padahal hidup butuh useful vulnerability juga.", ["kontemporer","sosmed","pemuda"]),
    ("Yang leras bukan keajaiban, tapi keteguhan iman di ujian", "Teguh dari Pagi sampai Malam", "Muhammad SAW tetap sholat fardhu meski lelah merantau ke Taslim.", ["sholat","iman","ujian","pemuda"]),
    ("Bahwa anda taat pada iman,咸阳 menjagalah pesanannya pada karakter (#keepgoing)", "Keep Going", "The grind is real, tapi iman lebih real.", ["motivasi","pemuda"]),
    ("Sahabatnya bukan cuma temen ngopi, tapi sahabat nge-ride mati.", "Sahabat Abu Bakar", "Abu Bakar: sahabat pertama yang percaya tanpa ragu.", ["sahabat","kisah","pemuda"]),
]

CAPTIONS_TEMPLATES = [
    "Cerita kecil nabi yang jarang diceritakan, tapi exactly vibe pemuda zaman now.\n\nApa yang bikin kamu merasa 'must keep going' hari ini?\n👇",
    "Kalau Rasul bisa ngelakuin ini, kamu juga bisa nge-rap kariermu.\n\nKetik di komen: ONE THING yang mau kamuLEVELUP minggu ini.\n👇",
    "Ketika dunia berteriak keras, Rasul menjawab dengan doa.\n\nAgama bukan cuma ritual, tapi energi buat setiap langkah hari ini.\n👇",
    "Gak cuma di ibadah, Rasul juga ngelakuin hal kecil dengan consistency. Bukalah.",
]

MEDIA_DESCRIPTIONS = [
    "Carousel: Quote + visual padang gembala + overlay teks.",
    "Reel: Hook 3 detik 'Nabi juga pernah kepinggiran'. Background: suara qori'. Text overlay.",
    "Image: Quote animation style. Gradient skyline Madinah.",
    "Reel: Before/after comparison - Rasul before vs after wahyu. Transition beat drop.",
    "Carousel: 3 slides - story, quote, CTA to follow.",
]

def create_content():
    os.environ['APP_KEY'] = 'change-me-to-random'
    if not os.path.exists('app.py'):
        print('Run dari folder content-hub ya'); return
    saved = []
    for i, (quote, title, caption, tags) in enumerate(QUOTES, 1):
        payload = {
            'title': title,
            'body': caption,
            'category': 'kisah',
            'affiliate_tags': tags
        }
        try:
            r = requests.post(f'{BASE}/api/content', json=payload, timeout=10)
            data = r.json()
            if r.ok or 'id' in data:
                saved.append(data['id'])
                print(f'OK {i}/{len(QUOTES)} id={data["id"]} {title}')
            else:
                print(f'FAIL {i} {data}')
        except Exception as e:
            print(f'ERR {i} {e}')
    print(f'\nSaved {len(saved)} items: {saved}')
    return saved

if __name__ == '__main__':
    create_content()
