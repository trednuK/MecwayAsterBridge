//! ASTER `.mail` writer. The bytes match `bridge_mesh._write_aster_mail`:
//! lines joined by newlines, element and group lines wrapped at 79 characters.

use std::fs::File;
use std::io::{self, BufWriter, Read, Write};
use std::path::Path;

use crate::real::real;

const WIDTH: usize = 79;

pub fn write_mail(path: &Path, mut input: impl Read) -> io::Result<()> {
    let f = File::create(path)?;
    let mut w = BufWriter::with_capacity(1 << 20, f);
    write_line(&mut w, "TITRE")?;
    write_line(&mut w, " Mecway-model via MecwayAsterBridge")?;
    write_line(&mut w, "FINSF")?;
    write_line(&mut w, "COOR_3D")?;
    write_coords(&mut w, &mut input)?;
    write_coords(&mut w, &mut input)?;
    write_line(&mut w, "FINSF")?;
    let n_types = read_u32(&mut input)?;
    for _ in 0..n_types {
        let atype = read_string(&mut input)?;
        write_line(&mut w, &atype)?;
        let n_cells = read_u32(&mut input)?;
        for _ in 0..n_cells {
            let name = read_string(&mut input)?;
            let n = read_u32(&mut input)? as usize;
            let mut items = Vec::with_capacity(n + 1);
            items.push(name);
            for _ in 0..n {
                items.push(format!("N{}", read_u32(&mut input)?));
            }
            write_wrapped(&mut w, &items)?;
        }
        write_line(&mut w, "FINSF")?;
    }
    let n_kinds = read_u32(&mut input)?;
    for _ in 0..n_kinds {
        let kind = read_string(&mut input)?;
        let n_groups = read_u32(&mut input)?;
        for _ in 0..n_groups {
            let name = read_string(&mut input)?;
            write_line(&mut w, &kind)?;
            write_line(&mut w, &format!(" {name}"))?;
            let n_members = read_u32(&mut input)?;
            let mut members = Vec::with_capacity(n_members as usize);
            for _ in 0..n_members {
                members.push(read_string(&mut input)?);
            }
            write_wrapped(&mut w, &members)?;
            write_line(&mut w, "FINSF")?;
        }
    }
    write_line(&mut w, "FIN")?;
    w.flush()?;
    Ok(())
}

fn write_coords(w: &mut impl Write, input: &mut impl Read) -> io::Result<()> {
    let n = read_u32(input)? as usize;
    let mut nids = Vec::with_capacity(n);
    for _ in 0..n {
        nids.push(read_u32(input)?);
    }
    let mut xyz = Vec::with_capacity(n * 3);
    for _ in 0..n * 3 {
        xyz.push(read_f64(input)?);
    }
    for i in 0..n {
        write_line(
            w,
            &format!(
                " N{} {} {} {}",
                nids[i],
                real(xyz[i * 3]),
                real(xyz[i * 3 + 1]),
                real(xyz[i * 3 + 2])
            ),
        )?;
    }
    Ok(())
}

fn write_line(w: &mut impl Write, line: &str) -> io::Result<()> {
    w.write_all(line.as_bytes())?;
    w.write_all(if cfg!(windows) { b"\r\n" } else { b"\n" })
}

fn write_wrapped(w: &mut impl Write, items: &[String]) -> io::Result<()> {
    let mut cur = String::new();
    for it in items {
        if !cur.is_empty() && cur.chars().count() + 1 + it.chars().count() > WIDTH {
            write_line(w, &cur)?;
            cur.clear();
        }
        cur.push(' ');
        cur.push_str(it);
    }
    if !cur.is_empty() {
        write_line(w, &cur)?;
    }
    Ok(())
}

fn read_u32(r: &mut impl Read) -> io::Result<u32> {
    let mut b = [0u8; 4];
    r.read_exact(&mut b)?;
    Ok(u32::from_le_bytes(b))
}

fn read_f64(r: &mut impl Read) -> io::Result<f64> {
    let mut b = [0u8; 8];
    r.read_exact(&mut b)?;
    Ok(f64::from_le_bytes(b))
}

fn read_string(r: &mut impl Read) -> io::Result<String> {
    let n = read_u32(r)? as usize;
    let mut b = vec![0u8; n];
    r.read_exact(&mut b)?;
    String::from_utf8(b).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
}
