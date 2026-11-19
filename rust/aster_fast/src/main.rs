//! aster_fast — the slow mesh steps of MecwayAsterBridge, outside IronPython.
//!
//!   aster_fast prep <model.liml> <slim.liml> <mesh.bin>
//!   aster_fast mail <model.mail>   (job on stdin, see Scripts/bridge_fast.py)

mod mail;
mod real;
mod scan;

use std::env;
use std::io::{self, Write};
use std::path::Path;
use std::process::ExitCode;

fn main() -> ExitCode {
    if let Err(err) = run() {
        let _ = writeln!(io::stderr(), "aster_fast: {err}");
        return ExitCode::from(1);
    }
    ExitCode::from(0)
}

fn run() -> io::Result<()> {
    let mut args = env::args().skip(1);
    let cmd = args.next().unwrap_or_default();
    match cmd.as_str() {
        "prep" => {
            let liml = need(&mut args, "liml")?;
            let slim = need(&mut args, "slim")?;
            let bin = need(&mut args, "bin")?;
            scan::prepare(Path::new(&liml), Path::new(&slim), Path::new(&bin))
        }
        "mail" => {
            let out = need(&mut args, "mail")?;
            mail::write_mail(Path::new(&out), io::stdin().lock())
        }
        _ => Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "usage: aster_fast prep <liml> <slim> <bin> | aster_fast mail <mail>",
        )),
    }
}

fn need(args: &mut impl Iterator<Item = String>, name: &str) -> io::Result<String> {
    args.next()
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, format!("missing {name}")))
}
