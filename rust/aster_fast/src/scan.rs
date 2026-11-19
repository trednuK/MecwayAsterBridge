//! Stream the model half of a Mecway `.liml` (everything before the
//! top-level `<solution`) into a slim XML plus the mesh records the
//! bridge used to pull out with ElementTree.

use std::fs::File;
use std::io::{self, BufReader, Read, Write};
use std::path::Path;

#[derive(Clone, Copy, PartialEq)]
enum Frame {
    Liml,
    Elset,
    FaceSel,
    ElemSel,
    NodeSel,
    Other,
}

struct Elem {
    eid: u32,
    shape: String,
    nodes: Vec<u32>,
    truss: bool,
    ux: Option<String>,
    uy: Option<String>,
    uz: Option<String>,
    vx: Option<String>,
    vy: Option<String>,
    vz: Option<String>,
    angle: Option<String>,
}

struct Elset {
    name: String,
    elems: Vec<Elem>,
    /// Shapes of an `<elem>` that has no `eid`. Python still puts those
    /// in the elset's shape set.
    extra_shapes: Vec<String>,
}

struct FaceSel {
    name: String,
    faces: Vec<(u32, u32)>,
}

struct IdSel {
    name: String,
    ids: Vec<u32>,
}

struct NodeSel {
    name: String,
    /// `nid` text as written. Python does `"N{0}".format(nid)` on that
    /// text, so `"01"` stays `"N01"`.
    ids: Vec<String>,
}

pub struct Mesh {
    nodes: Vec<(u32, f64, f64, f64)>,
    elsets: Vec<Elset>,
    faces: Vec<FaceSel>,
    elemsels: Vec<IdSel>,
    nodesels: Vec<NodeSel>,
}

impl Mesh {
    fn new() -> Mesh {
        Mesh {
            nodes: Vec::new(),
            elsets: Vec::new(),
            faces: Vec::new(),
            elemsels: Vec::new(),
            nodesels: Vec::new(),
        }
    }
}

pub fn prepare(liml: &Path, slim_path: &Path, bin_path: &Path) -> io::Result<()> {
    let (data, cut) = read_model(liml)?;
    let mut slim = Vec::with_capacity(data.len() / 8 + 64);
    let mut mesh = Mesh::new();
    parse(&data, &mut slim, &mut mesh)?;
    if cut {
        slim.extend_from_slice(b"</liml>");
    }
    {
        let mut f = File::create(slim_path)?;
        f.write_all(&slim)?;
    }
    {
        let mut f = File::create(bin_path)?;
        write_bin(&mut f, &mesh)?;
    }
    Ok(())
}

/// Bytes of the model, cut at the same `<solution` Python's `_model_bytes` uses.
fn read_model(path: &Path) -> io::Result<(Vec<u8>, bool)> {
    let f = File::open(path)?;
    let mut r = BufReader::new(f);
    let mut data = Vec::new();
    let mut buf = [0u8; 1 << 20];
    let pat = b"<solution";
    loop {
        let n = r.read(&mut buf)?;
        if n == 0 {
            return Ok((data, false));
        }
        let search_from = data.len().saturating_sub(pat.len() + 1);
        data.extend_from_slice(&buf[..n]);
        if let Some(pos) = find_solution_from(&data, pat, search_from) {
            data.truncate(pos);
            return Ok((data, true));
        }
    }
}

fn find_solution_from(data: &[u8], pat: &[u8], start: usize) -> Option<usize> {
    let follow = b">/ \t\r\n";
    let mut from = start;
    while let Some(rel) = find_from(data, pat, from) {
        let after = rel + pat.len();
        if after >= data.len() {
            return None;
        }
        if follow.contains(&data[after]) {
            return Some(rel);
        }
        from = rel + 1;
    }
    None
}

fn find_from(data: &[u8], pat: &[u8], start: usize) -> Option<usize> {
    if start >= data.len() || data.len() - start < pat.len() {
        return None;
    }
    data[start..]
        .windows(pat.len())
        .position(|w| w == pat)
        .map(|p| p + start)
}

fn parse(data: &[u8], slim: &mut Vec<u8>, mesh: &mut Mesh) -> io::Result<()> {
    let mut i = 0;
    let mut stack: Vec<Frame> = Vec::new();
    while i < data.len() {
        if data[i] != b'<' {
            let start = i;
            while i < data.len() && data[i] != b'<' {
                i += 1;
            }
            slim.extend_from_slice(&data[start..i]);
            continue;
        }
        if data[i..].starts_with(b"<!--") {
            let end = find_bytes(&data[i..], b"-->").map(|p| i + p + 3);
            let end = end.unwrap_or(data.len());
            slim.extend_from_slice(&data[i..end]);
            i = end;
            continue;
        }
        if data[i..].starts_with(b"<?") {
            let end = find_bytes(&data[i..], b"?>").map(|p| i + p + 2);
            let end = end.unwrap_or(data.len());
            slim.extend_from_slice(&data[i..end]);
            i = end;
            continue;
        }
        let start = i;
        let end = match find_tag_end(data, i) {
            Some(e) => e,
            None => {
                slim.extend_from_slice(&data[i..]);
                break;
            }
        };
        let raw = &data[start..end];
        i = end;
        let info = match tag_info(raw) {
            Some(t) => t,
            None => {
                slim.extend_from_slice(raw);
                continue;
            }
        };
        if info.closing {
            stack.pop();
            slim.extend_from_slice(raw);
            continue;
        }
        // Top-level <solution ...>: same cut as _model_bytes, then stop.
        // read_model already drops this when the follow byte is present;
        // this is the same rule if the tag is still in the buffer.
        if info.name == b"solution"
            && stack.len() == 1
            && stack[0] == Frame::Liml
            && !info.closing
        {
            slim.extend_from_slice(b"</liml>");
            break;
        }
        let parent = stack.last().copied();
        let drop = take_tag(info.name, parent, raw, mesh)?;
        if !drop {
            slim.extend_from_slice(raw);
        }
        if !info.self_close {
            stack.push(frame_of(info.name, parent));
        }
    }
    Ok(())
}

struct TagInfo<'a> {
    name: &'a [u8],
    closing: bool,
    self_close: bool,
}

fn tag_info(raw: &[u8]) -> Option<TagInfo<'_>> {
    if raw.len() < 3 || raw[0] != b'<' || raw[raw.len() - 1] != b'>' {
        return None;
    }
    let mut body = &raw[1..raw.len() - 1];
    let self_close = body.ends_with(b"/");
    if self_close {
        body = &body[..body.len() - 1];
    }
    let closing = body.starts_with(b"/");
    if closing {
        body = &body[1..];
    }
    let name_len = body
        .iter()
        .position(|&c| c == b' ' || c == b'\t' || c == b'\r' || c == b'\n' || c == b'/')
        .unwrap_or(body.len());
    if name_len == 0 {
        return None;
    }
    Some(TagInfo {
        name: &body[..name_len],
        closing,
        self_close,
    })
}

fn frame_of(name: &[u8], parent: Option<Frame>) -> Frame {
    match (name, parent) {
        (b"liml", _) => Frame::Liml,
        (b"elset", Some(Frame::Liml)) => Frame::Elset,
        (b"faceselection", Some(Frame::Liml)) => Frame::FaceSel,
        (b"elementselection", Some(Frame::Liml)) => Frame::ElemSel,
        (b"nodeselection", Some(Frame::Liml)) => Frame::NodeSel,
        _ => Frame::Other,
    }
}

fn take_tag(
    name: &[u8],
    parent: Option<Frame>,
    raw: &[u8],
    mesh: &mut Mesh,
) -> io::Result<bool> {
    match name {
        b"node" if parent == Some(Frame::Liml) => {
            let inner = inner_bytes(raw);
            let nid_text = match attr(inner, b"nid") {
                Some(s) => s,
                None => return Ok(false),
            };
            let nid = parse_u32(&nid_text)?;
            let x = match attr(inner, b"x") {
                Some(s) => parse_f64(&s)?,
                None => 0.0,
            };
            let y = match attr(inner, b"y") {
                Some(s) => parse_f64(&s)?,
                None => 0.0,
            };
            let z = match attr(inner, b"z") {
                Some(s) => parse_f64(&s)?,
                None => 0.0,
            };
            mesh.nodes.push((nid, x, y, z));
            Ok(true)
        }
        b"node" if parent == Some(Frame::NodeSel) => {
            let inner = inner_bytes(raw);
            if let Some(text) = attr(inner, b"nid") {
                if let Some(sel) = mesh.nodesels.last_mut() {
                    sel.ids.push(text);
                }
            }
            Ok(true)
        }
        b"elset" if parent == Some(Frame::Liml) => {
            let inner = inner_bytes(raw);
            let name = attr_string(inner, b"name").unwrap_or_else(|_| "Default".to_string());
            mesh.elsets.push(Elset {
                name,
                elems: Vec::new(),
                extra_shapes: Vec::new(),
            });
            Ok(false)
        }
        b"elem" if parent == Some(Frame::Elset) => {
            let inner = inner_bytes(raw);
            let shape = match attr(inner, b"shape") {
                Some(s) => s,
                None => return Ok(true),
            };
            let eid = match attr(inner, b"eid") {
                Some(s) => parse_u32(&s)?,
                None => {
                    if let Some(elset) = mesh.elsets.last_mut() {
                        elset.extra_shapes.push(shape);
                    }
                    return Ok(true);
                }
            };
            let nodes = match attr(inner, b"nodes") {
                Some(s) => parse_nodes(&s)?,
                None => Vec::new(),
            };
            let truss = attr(inner, b"truss").as_deref() == Some("true");
            let elem = Elem {
                eid,
                shape,
                nodes,
                truss,
                ux: attr(inner, b"orientationux"),
                uy: attr(inner, b"orientationuy"),
                uz: attr(inner, b"orientationuz"),
                vx: attr(inner, b"orientationvx"),
                vy: attr(inner, b"orientationvy"),
                vz: attr(inner, b"orientationvz"),
                angle: attr(inner, b"angle"),
            };
            if let Some(elset) = mesh.elsets.last_mut() {
                elset.elems.push(elem);
            }
            Ok(true)
        }
        b"faceselection" if parent == Some(Frame::Liml) => {
            let inner = inner_bytes(raw);
            let name = attr_string(inner, b"name").unwrap_or_default();
            mesh.faces.push(FaceSel {
                name,
                faces: Vec::new(),
            });
            Ok(false)
        }
        b"face" if parent == Some(Frame::FaceSel) => {
            let inner = inner_bytes(raw);
            if let Some(eid) = attr(inner, b"eid") {
                let eid = parse_u32(&eid)?;
                let faceid = parse_u32(attr(inner, b"faceid").as_deref().unwrap_or("0"))?;
                if let Some(sel) = mesh.faces.last_mut() {
                    sel.faces.push((eid, faceid));
                }
            }
            Ok(true)
        }
        b"elementselection" if parent == Some(Frame::Liml) => {
            let inner = inner_bytes(raw);
            let name = attr_string(inner, b"name").unwrap_or_default();
            mesh.elemsels.push(IdSel {
                name,
                ids: Vec::new(),
            });
            Ok(false)
        }
        b"element" if parent == Some(Frame::ElemSel) => {
            let inner = inner_bytes(raw);
            if let Some(eid) = attr(inner, b"eid") {
                let eid = parse_u32(&eid)?;
                if let Some(sel) = mesh.elemsels.last_mut() {
                    sel.ids.push(eid);
                }
            }
            Ok(true)
        }
        b"nodeselection" if parent == Some(Frame::Liml) => {
            let inner = inner_bytes(raw);
            let name = attr_string(inner, b"name").unwrap_or_default();
            mesh.nodesels.push(NodeSel {
                name,
                ids: Vec::new(),
            });
            Ok(false)
        }
        _ => Ok(false),
    }
}

fn inner_bytes(raw: &[u8]) -> &[u8] {
    let mut body = &raw[1..raw.len() - 1];
    if body.ends_with(b"/") {
        body = &body[..body.len() - 1];
    }
    body
}

fn attr(inner: &[u8], key: &[u8]) -> Option<String> {
    let mut i = 0;
    while i < inner.len() {
        while i < inner.len() && inner[i].is_ascii_whitespace() {
            i += 1;
        }
        if i >= inner.len() {
            break;
        }
        let ks = i;
        while i < inner.len() && inner[i] != b'=' && !inner[i].is_ascii_whitespace() {
            i += 1;
        }
        let name = &inner[ks..i];
        while i < inner.len() && inner[i].is_ascii_whitespace() {
            i += 1;
        }
        if i >= inner.len() || inner[i] != b'=' {
            continue;
        }
        i += 1;
        while i < inner.len() && inner[i].is_ascii_whitespace() {
            i += 1;
        }
        if i >= inner.len() {
            break;
        }
        let quote = inner[i];
        if quote != b'"' && quote != b'\'' {
            continue;
        }
        i += 1;
        let vs = i;
        while i < inner.len() && inner[i] != quote {
            i += 1;
        }
        let value = &inner[vs..i];
        if i < inner.len() {
            i += 1;
        }
        if name == key {
            return Some(decode(value));
        }
    }
    None
}

fn attr_string(inner: &[u8], key: &[u8]) -> io::Result<String> {
    attr(inner, key).ok_or_else(|| {
        io::Error::new(
            io::ErrorKind::InvalidData,
            format!("missing attribute {}", String::from_utf8_lossy(key)),
        )
    })
}

fn decode(raw: &[u8]) -> String {
    let text = match std::str::from_utf8(raw) {
        Ok(s) => s,
        Err(_) => return String::from_utf8_lossy(raw).into_owned(),
    };
    if !text.contains('&') {
        return text.to_string();
    }
    let bytes = text.as_bytes();
    let mut out = String::with_capacity(text.len());
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'&' {
            if let Some(rel) = text[i + 1..].find(';') {
                let ent = &text[i + 1..i + 1 + rel];
                if let Some(repl) = entity(ent) {
                    out.push_str(&repl);
                    i += rel + 2;
                    continue;
                }
            }
        }
        let ch = text[i..].chars().next().unwrap();
        out.push(ch);
        i += ch.len_utf8();
    }
    out
}

fn entity(ent: &str) -> Option<String> {
    match ent {
        "amp" => Some("&".to_string()),
        "lt" => Some("<".to_string()),
        "gt" => Some(">".to_string()),
        "quot" => Some("\"".to_string()),
        "apos" => Some("'".to_string()),
        _ => {
            let num = ent.strip_prefix('#')?;
            let code = if let Some(hex) = num.strip_prefix('x').or_else(|| num.strip_prefix('X'))
            {
                u32::from_str_radix(hex, 16).ok()?
            } else {
                num.parse::<u32>().ok()?
            };
            char::from_u32(code).map(|c| c.to_string())
        }
    }
}

fn parse_u32(text: &str) -> io::Result<u32> {
    let text = text.trim();
    if let Ok(v) = text.parse::<u32>() {
        return Ok(v);
    }
    if let Ok(v) = text.parse::<i64>() {
        if (0..i64::from(u32::MAX) + 1).contains(&v) {
            return Ok(v as u32);
        }
    }
    Err(io::Error::new(
        io::ErrorKind::InvalidData,
        format!("not an integer: {text}"),
    ))
}

fn parse_f64(text: &str) -> io::Result<f64> {
    text.trim().parse::<f64>().map_err(|_| {
        io::Error::new(
            io::ErrorKind::InvalidData,
            format!("not a float: {text}"),
        )
    })
}

fn parse_nodes(text: &str) -> io::Result<Vec<u32>> {
    let mut out = Vec::new();
    for part in text.split_whitespace() {
        out.push(parse_u32(part)?);
    }
    Ok(out)
}

fn find_tag_end(data: &[u8], start: usize) -> Option<usize> {
    let mut i = start + 1;
    let mut quote = 0u8;
    while i < data.len() {
        let c = data[i];
        if quote != 0 {
            if c == quote {
                quote = 0;
            }
            i += 1;
            continue;
        }
        if c == b'"' || c == b'\'' {
            quote = c;
            i += 1;
            continue;
        }
        if c == b'>' {
            return Some(i + 1);
        }
        i += 1;
    }
    None
}

fn find_bytes(data: &[u8], pat: &[u8]) -> Option<usize> {
    if data.len() < pat.len() {
        return None;
    }
    data.windows(pat.len()).position(|w| w == pat)
}

fn write_bin(w: &mut impl Write, mesh: &Mesh) -> io::Result<()> {
    w.write_all(b"MWFAST1")?;
    write_u32(w, mesh.nodes.len() as u32)?;
    for (nid, _, _, _) in &mesh.nodes {
        write_u32(w, *nid)?;
    }
    for (_, x, y, z) in &mesh.nodes {
        write_f64(w, *x)?;
        write_f64(w, *y)?;
        write_f64(w, *z)?;
    }
    write_u32(w, mesh.elsets.len() as u32)?;
    for elset in &mesh.elsets {
        write_str(w, &elset.name)?;
        write_u32(w, elset.elems.len() as u32)?;
        for e in &elset.elems {
            write_u32(w, e.eid)?;
            write_str(w, &e.shape)?;
            write_u32(w, e.nodes.len() as u32)?;
            for n in &e.nodes {
                write_u32(w, *n)?;
            }
            let mut flags = 0u8;
            if e.truss {
                flags |= 1;
            }
            if e.ux.is_some() {
                flags |= 1 << 1;
            }
            if e.uy.is_some() {
                flags |= 1 << 2;
            }
            if e.uz.is_some() {
                flags |= 1 << 3;
            }
            if e.vx.is_some() {
                flags |= 1 << 4;
            }
            if e.vy.is_some() {
                flags |= 1 << 5;
            }
            if e.vz.is_some() {
                flags |= 1 << 6;
            }
            if e.angle.is_some() {
                flags |= 1 << 7;
            }
            w.write_all(&[flags])?;
            for part in [&e.ux, &e.uy, &e.uz, &e.vx, &e.vy, &e.vz] {
                if let Some(text) = part {
                    write_str(w, text)?;
                }
            }
            if let Some(text) = &e.angle {
                write_str(w, text)?;
            }
        }
        write_u32(w, elset.extra_shapes.len() as u32)?;
        for shape in &elset.extra_shapes {
            write_str(w, shape)?;
        }
    }
    write_u32(w, mesh.faces.len() as u32)?;
    for sel in &mesh.faces {
        write_str(w, &sel.name)?;
        write_u32(w, sel.faces.len() as u32)?;
        for (eid, faceid) in &sel.faces {
            write_u32(w, *eid)?;
            write_u32(w, *faceid)?;
        }
    }
    write_u32(w, mesh.elemsels.len() as u32)?;
    for sel in &mesh.elemsels {
        write_str(w, &sel.name)?;
        write_u32(w, sel.ids.len() as u32)?;
        for id in &sel.ids {
            write_u32(w, *id)?;
        }
    }
    write_u32(w, mesh.nodesels.len() as u32)?;
    for sel in &mesh.nodesels {
        write_str(w, &sel.name)?;
        write_u32(w, sel.ids.len() as u32)?;
        for id in &sel.ids {
            write_str(w, id)?;
        }
    }
    Ok(())
}

fn write_u32(w: &mut impl Write, v: u32) -> io::Result<()> {
    w.write_all(&v.to_le_bytes())
}

fn write_f64(w: &mut impl Write, v: f64) -> io::Result<()> {
    w.write_all(&v.to_le_bytes())
}

fn write_str(w: &mut impl Write, text: &str) -> io::Result<()> {
    let b = text.as_bytes();
    if b.len() > u32::MAX as usize {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "string too long"));
    }
    write_u32(w, b.len() as u32)?;
    w.write_all(b)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slim_drops_mesh_and_solution_nodes() {
        let xml = br#"<liml version="1">
  <node nid="1" x="1.5" y="0" z="-2" />
  <elset name="A&B">
    <elem eid="1" shape="line2" nodes="1 2" truss="true" />
    <elem shape="line3" />
  </elset>
  <nodeselection name="Vast">
    <node nid="01" />
  </nodeselection>
  <mat name="S" />
  <solution>
    <node nid="9" x="0" y="0" z="0" />
  </solution>
</liml>"#;
        let mut slim = Vec::new();
        let mut mesh = Mesh::new();
        parse(xml, &mut slim, &mut mesh).unwrap();
        let text = String::from_utf8(slim).unwrap();
        assert!(text.contains("<mat name=\"S\" />"), "{text}");
        assert!(text.contains("name=\"A&B\""), "{text}");
        assert!(!text.contains("nid=\"9\""), "{text}");
        assert!(!text.contains("<elem"), "{text}");
        assert!(text.trim_end().ends_with("</liml>"), "{text}");
        assert_eq!(mesh.nodes.len(), 1);
        assert_eq!(mesh.nodes[0].0, 1);
        assert_eq!(mesh.nodes[0].1, 1.5);
        assert_eq!(mesh.elsets[0].name, "A&B");
        assert_eq!(mesh.elsets[0].elems.len(), 1);
        assert!(mesh.elsets[0].elems[0].truss);
        assert_eq!(mesh.elsets[0].extra_shapes, vec!["line3".to_string()]);
        assert_eq!(mesh.nodesels[0].ids, vec!["01".to_string()]);
    }
}
