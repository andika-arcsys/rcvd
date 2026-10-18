//! Shell desktop. Pada build rilis, engine Python dijalankan sebagai sidecar.
//! Mode debug tidak memunculkan sidecar: engine dijalankan terpisah saat pengembangan.

use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

struct EngineProcess(std::sync::Mutex<Option<CommandChild>>);

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            if !cfg!(debug_assertions) {
                let child = start_engine(app.handle())?;
                app.manage(EngineProcess(std::sync::Mutex::new(Some(child))));
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("gagal menjalankan DeepInsight")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(state) = app.try_state::<EngineProcess>() {
                    if let Ok(mut slot) = state.0.lock() {
                        if let Some(child) = slot.take() {
                            let _ = child.kill();
                        }
                    }
                }
            }
        });
}

fn start_engine(app: &tauri::AppHandle) -> tauri::Result<CommandChild> {
    let token = format!("{:x}-{}", std::process::id(), std::process::id().wrapping_mul(17));
    if let Some(window) = app.get_webview_window("main") {
        let script = format!(
            "window.__DEEPINSIGHT__ = {{ baseUrl: 'http://127.0.0.1:8765', token: '{token}' }};"
        );
        let _ = window.eval(&script);
    }
    let config = app.path().resource_dir()?.join("config");
    let (_rx, child) = app
        .shell()
        .sidecar("deepinsight-engine")?
        .env("DEEPINSIGHT_TOKEN", token)
        .env("DEEPINSIGHT_CONFIG_DIR", config)
        .spawn()?;
    Ok(child)
}
