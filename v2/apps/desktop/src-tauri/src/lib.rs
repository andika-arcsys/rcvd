//! Shell desktop DeepInsight. Logika bisnis ada di engine Python, bukan di sini.
//! Supervisor engine (jalankan, token acak, hentikan) ditambahkan pada fase berikutnya.

pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("gagal menjalankan DeepInsight");
}
