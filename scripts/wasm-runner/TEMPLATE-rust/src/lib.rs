//! TEMPLATE — compile a toy-language interpreter to the ToyPLCollector wasm ABI
//!
//! Copy this folder, swap `interpret()` below for your real lexer/parser/
//! evaluator, then:
//!
//!   rustup target add wasm32-unknown-unknown
//!   cargo build --release --target wasm32-unknown-unknown
//!   # → target/wasm32-unknown-unknown/release/yourlang_wasm.wasm
//!
//! Contract (full docs in ../../CONTRIBUTING.md):
//!   exports: memory, alloc(size:i32)->i32, run(ptr:i32,len:i32)->i32
//!   imports: toypl.output(ptr:i32,len:i32), toypl.exit(code:i32)

#![no_std]
use core::panic::PanicInfo;

// ---- imports the page provides (do not rename) --------------------------
#[link(wasm_import_module = "toypl")]
extern "C" {
    fn output(ptr: i32, len: i32);
    fn exit(code: i32) -> !;
}

// ---- bump allocator over a static buffer --------------------------------
// In wasm32, "addresses" are offsets into linear memory, so the offset of a
// static is its real address. Memory itself is exported by wasm-ld by
// default; if you outgrow the static buffer use a real allocator
// (e.g. wee_alloc) + `memory.grow` instead.
static mut HEAP: [u8; 1 << 16] = [0; 1 << 16];
static mut HEAP_TOP: usize = 0;

fn alloc_bytes(len: usize) -> usize {
    let base = core::ptr::addr_of!(HEAP) as usize;
    let top = unsafe {
        let t = core::ptr::addr_of_mut!(HEAP_TOP).read();
        core::ptr::addr_of_mut!(HEAP_TOP).write(t + len);
        t
    };
    base + top
}

#[no_mangle]
pub extern "C" fn alloc(size: i32) -> i32 {
    alloc_bytes(size as usize) as i32
}

fn toy_write(bytes: &[u8]) {
    unsafe { output(bytes.as_ptr() as i32, bytes.len() as i32) }
}

// ---- your language goes here ---------------------------------------------
fn interpret(src: &str) {
    // Demo: parse nothing, just echo that we received the program.
    toy_write(b"[yourlang] program received: ");
    toy_write(src.as_bytes());
    toy_write(b"\nHello, World!\n");
}

// ---- page -> language entry point (do not rename) -------------------------
#[no_mangle]
pub extern "C" fn run(ptr: i32, len: i32) -> i32 {
    let bytes: &[u8] = unsafe { core::slice::from_raw_parts(ptr as *const u8, len as usize) };
    match core::str::from_utf8(bytes) {
        Ok(src) => {
            interpret(src);
            0
        }
        Err(_) => {
            toy_write(b"[yourlang] source is not valid UTF-8\n");
            1
        }
    }
}

// ---- exports must exist on wasm32-unknown-unknown -------------------------
#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    unsafe { exit(101) }
}
