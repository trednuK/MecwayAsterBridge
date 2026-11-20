//! Read a Code-Aster `.rmed` and write the `<results>` fragment
//! `Scripts/bridge_med.py` writes. The Python reader stays as the fallback
//! when this program is missing or the file uses an HDF5 feature it cannot
//! read. No libhdf5: `hdf5-pure` (deflate and shuffle included).

use std::collections::HashMap;
use std::fs::File;
use std::io::{self, BufWriter, Write};
use std::path::Path;

use hdf5_pure::{AttrValue, Dataset, File as H5File, Group};

use crate::scan;

const NO_PROFILE: &str = "MED_NO_PROFILE_INTERNAL";

/// (med field, component, mecway name, element-node?)
const MAP: &[(&str, &str, &str, bool)] = &[
    ("DEPL", "DX", "displx", false),
    ("DEPL", "DY", "disply", false),
    ("DEPL", "DZ", "displz", false),
    ("DEPL", "DRX", "rotx", false),
    ("DEPL", "DRY", "roty", false),
    ("DEPL", "DRZ", "rotz", false),
    ("SIGM_NOEU", "SIXX", "stressxx", false),
    ("SIGM_NOEU", "SIYY", "stressyy", false),
    ("SIGM_NOEU", "SIZZ", "stresszz", false),
    ("SIGM_NOEU", "SIXY", "stressxy", false),
    ("SIGM_NOEU", "SIYZ", "stressyz", false),
    ("SIGM_NOEU", "SIXZ", "stresszx", false),
    ("SIEQ_NOEU", "VMIS", "vonmises", false),
    ("res_sup", "VMIS", "vonmisesu1", false),
    ("res_moy", "VMIS", "vonmisesm", false),
    ("res_inf", "VMIS", "vonmisesb", false),
    ("REAC_NODA", "DX", "reactionforcex", false),
    ("REAC_NODA", "DY", "reactionforcey", false),
    ("REAC_NODA", "DZ", "reactionforcez", false),
    ("REAC_NODA", "DRX", "reactionmomx", false),
    ("REAC_NODA", "DRY", "reactionmomy", false),
    ("REAC_NODA", "DRZ", "reactionmomz", false),
    ("TEMP", "TEMP", "temperature", false),
    ("FLUX_NOEU", "FLUX", "heatfluxx", false),
    ("FLUX_NOEU", "FLUY", "heatfluxy", false),
    ("FLUX_NOEU", "FLUZ", "heatfluxz", false),
    ("SIGM_ELNO", "SIXX", "stressxx", true),
    ("SIGM_ELNO", "SIYY", "stressyy", true),
    ("SIGM_ELNO", "SIZZ", "stresszz", true),
    ("SIGM_ELNO", "SIXY", "stressxy", true),
    ("SIGM_ELNO", "SIYZ", "stressyz", true),
    ("SIGM_ELNO", "SIXZ", "stresszx", true),
    ("SIEQ_ELNO", "VMIS", "vonmises", true),
];

struct Node {
    id: i32,
}

struct Cell {
    eid: i32,
    nodes: Vec<i32>,
}

/// One gauss point is one component row. `NGA <= 1` is a nodal row.
struct Entity {
    nodal: Option<Vec<f64>>,
    elno: Option<Vec<Vec<f64>>>,
}

struct Step {
    time: f64,
    /// Row i belongs to mesh node i, as `bridge_med._field`.
    nodal: Vec<Entity>,
    /// MED element type -> row i belongs to cell i of that type.
    elno: HashMap<String, Vec<Entity>>,
}

struct Field {
    comps: Vec<String>,
    steps: Vec<Step>,
}

struct Var {
    name: String,
    elno: bool,
    /// Node ids, or element ids, sorted.
    ids: Vec<i32>,
    /// One flat buffer per time. Element-node values are concatenated in
    /// `ids` order, Mecway node order inside each element.
    steps: Vec<Vec<f64>>,
    times: Vec<f64>,
}

pub fn write_fragment(rmed: &Path, out: &Path, liml: Option<&Path>) -> io::Result<()> {
    stage("start");
    let model = match liml {
        Some(path) => {
            stage("reading the model for element order");
            match scan::model_mesh(path) {
                Ok(m) => Some(m),
                Err(e) => {
                    stage(&format!("model skipped: {e}"));
                    None
                }
            }
        }
        None => None,
    };
    let bytes = std::fs::metadata(rmed).map(|m| m.len()).unwrap_or(0);
    stage(&format!("opening {bytes} bytes"));
    let file = H5File::open_streaming(rmed).or_else(|_| H5File::open(rmed)).map_err(err)?;
    stage("mesh");
    let (nodes, cells) = mesh(&file)?;
    let ncells: usize = cells.values().map(|v| v.len()).sum();
    stage(&format!("mesh {} nodes, {} elements", nodes.len(), ncells));
    let fields = fields(&file, &nodes, &cells)?;
    let vars = present(&fields, &nodes, &cells, model.as_ref())?;
    if vars.is_empty() {
        let names: Vec<&str> = fields.keys().map(|s| s.as_str()).collect();
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!("no Mecway field in the MED file (groups: {})", names.join(", ")),
        ));
    }
    let n = vars.len();
    stage(&format!("writing {n} variables"));
    let mut w = BufWriter::new(File::create(out)?);
    write_xml(&mut w, &vars, &nodes, model.as_ref())?;
    w.flush()?;
    println!("variables {n}");
    stage("done");
    Ok(())
}

fn stage(msg: &str) {
    let mut err = io::stderr();
    let _ = writeln!(err, "{msg}");
    let _ = err.flush();
}

fn err(e: impl std::fmt::Display) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, e.to_string())
}

fn mesh(file: &H5File) -> io::Result<(Vec<Node>, HashMap<String, Vec<Cell>>)> {
    let meshes = file.group("ENS_MAA").map_err(err)?;
    let names = meshes.groups().map_err(err)?;
    let mesh_name = names.first().ok_or_else(|| {
        io::Error::new(io::ErrorKind::InvalidData, "MED file has no mesh")
    })?;
    let mesh = meshes.group(mesh_name).map_err(err)?;
    let body = if mesh.group("NOE").is_ok() {
        mesh
    } else {
        let mut found = None;
        for key in mesh.groups().map_err(err)? {
            let child = mesh.group(&key).map_err(err)?;
            if child.group("NOE").is_ok() {
                found = Some(child);
                break;
            }
        }
        found.ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "MED mesh has no nodes"))?
    };
    let noe = body.group("NOE").map_err(err)?;
    let coo = noe.dataset("COO").map_err(err)?;
    let flat = coo.read_f64().map_err(err)?;
    let nbr = attr_i64(&coo, "NBR").unwrap_or(0);
    if nbr <= 0 {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "MED mesh has no nodes"));
    }
    let nbr = nbr as usize;
    let dim = if nbr == 0 { 0 } else { flat.len() / nbr };
    let _coords = fortran_f64(&flat, nbr, dim);
    let nums = read_opt_ints(noe.dataset("NUM"));
    let mut nodes = Vec::with_capacity(nbr);
    for i in 0..nbr {
        let id = nums.as_ref().and_then(|v| v.get(i).copied()).unwrap_or((i as i64) + 1);
        nodes.push(Node { id: id as i32 });
    }
    let mut index_to_nid = HashMap::new();
    for (i, node) in nodes.iter().enumerate() {
        index_to_nid.insert((i as i32) + 1, node.id);
    }
    let mut cells = HashMap::new();
    if let Ok(mai) = body.group("MAI") {
        for typ in mai.groups().map_err(err)? {
            let grp = mai.group(&typ).map_err(err)?;
            let Ok(nod) = grp.dataset("NOD") else { continue };
            let ncell = attr_i64(&nod, "NBR").unwrap_or(0);
            if ncell <= 0 {
                continue;
            }
            let ncell = ncell as usize;
            let flat_i = read_ints(&nod)?;
            let npe = flat_i.len() / ncell;
            let conn = fortran_i64(&flat_i, ncell, npe);
            let nums = read_opt_ints(grp.dataset("NUM"));
            let mut block = Vec::with_capacity(ncell);
            for i in 0..ncell {
                let eid = nums.as_ref().and_then(|v| v.get(i).copied()).unwrap_or((i as i64) + 1);
                let nodes = conn[i]
                    .iter()
                    .map(|k| index_to_nid.get(&(*k as i32)).copied().unwrap_or(*k as i32))
                    .collect();
                block.push(Cell { eid: eid as i32, nodes });
            }
            cells.insert(typ, block);
        }
    }
    Ok((nodes, cells))
}

fn fields(
    file: &H5File,
    nodes: &[Node],
    cells: &HashMap<String, Vec<Cell>>,
) -> io::Result<HashMap<String, Field>> {
    let Ok(cha) = file.group("CHA") else {
        return Ok(HashMap::new());
    };
    let mut out = HashMap::new();
    for name in cha.groups().map_err(err)? {
        if !wanted(&name) {
            continue;
        }
        stage(&format!("field {name}"));
        let group = cha.group(&name).map_err(err)?;
        let comps = components(&attr_text_group(&group, "NOM"));
        let mut keys = group.groups().map_err(err)?;
        keys.sort();
        let mut steps = Vec::new();
        for key in keys {
            let step = group.group(&key).map_err(err)?;
            let time = attr_f64_group(&step, "PDT").unwrap_or(0.0);
            let mut nodal = Vec::new();
            if let Ok(noe) = step.group("NOE") {
                let rows = profile(&noe)?;
                nodal = rows
                    .into_iter()
                    .enumerate()
                    .map(|(i, row)| {
                        if i < nodes.len() {
                            if let Entity { nodal: Some(_), .. } = &row {
                                return row;
                            }
                        }
                        Entity { nodal: None, elno: None }
                    })
                    .collect();
            }
            let mut elno = HashMap::new();
            for sub in step.groups().map_err(err)? {
                if !sub.starts_with("NOE.") {
                    continue;
                }
                let typ = sub.split_once('.').map(|(_, t)| t.to_string()).unwrap_or_default();
                let support = step.group(&sub).map_err(err)?;
                let rows = profile(&support)?;
                let block = cells.get(&typ).map(|v| v.len()).unwrap_or(0);
                let stored: Vec<Entity> = rows
                    .into_iter()
                    .enumerate()
                    .map(|(i, row)| {
                        if i < block {
                            if let Entity { elno: Some(_), .. } = &row {
                                return row;
                            }
                        }
                        Entity { nodal: None, elno: None }
                    })
                    .collect();
                if stored.iter().any(|e| e.elno.is_some()) {
                    elno.insert(typ, stored);
                }
            }
            steps.push(Step { time, nodal, elno });
        }
        out.insert(name, Field { comps, steps });
    }
    Ok(out)
}

fn profile(support: &Group) -> io::Result<Vec<Entity>> {
    let profile = {
        let text = attr_text_group(support, "PFL");
        if text.is_empty() { NO_PROFILE.to_string() } else { text }
    };
    let data = if support.group(&profile).is_ok() {
        support.group(&profile).map_err(err)?
    } else if support.dataset("CO").is_ok() {
        // CO sits on the support itself. Attributes may be there too.
        return profile_co(support, support.dataset("CO").map_err(err)?);
    } else {
        return Ok(Vec::new());
    };
    let co = match data.dataset("CO") {
        Ok(ds) => ds,
        Err(_) => return Ok(Vec::new()),
    };
    profile_co(&data, co)
}

fn profile_co(data: &Group, co: Dataset) -> io::Result<Vec<Entity>> {
    let nbr = attr_i64(&co, "NBR")
        .or_else(|| attr_i64_group(data, "NBR"))
        .unwrap_or(0);
    let nga = attr_i64(&co, "NGA")
        .or_else(|| attr_i64_group(data, "NGA"))
        .unwrap_or(1)
        .max(1) as usize;
    let flat = co.read_f64().map_err(err)?;
    if nbr <= 0 || flat.is_empty() {
        return Ok(Vec::new());
    }
    let nbr = nbr as usize;
    let ncomp = flat.len() / (nbr * nga);
    if ncomp == 0 {
        return Ok(Vec::new());
    }
    if nga <= 1 {
        return Ok(fortran_f64(&flat, nbr, ncomp)
            .into_iter()
            .map(|row| Entity { nodal: Some(row), elno: None })
            .collect());
    }
    let span = nbr * nga;
    let mut rows = Vec::with_capacity(nbr);
    for i in 0..nbr {
        let mut points = Vec::with_capacity(nga);
        for g in 0..nga {
            let mut comps = Vec::with_capacity(ncomp);
            for c in 0..ncomp {
                comps.push(flat[i + g * nbr + c * span]);
            }
            points.push(comps);
        }
        rows.push(Entity { nodal: None, elno: Some(points) });
    }
    Ok(rows)
}

fn present(
    fields: &HashMap<String, Field>,
    nodes: &[Node],
    cells: &HashMap<String, Vec<Cell>>,
    model: Option<&scan::ModelMesh>,
) -> io::Result<Vec<Var>> {
    let mut found: Vec<(String, &str, &str, bool)> = Vec::new();
    let mut depl_key: Option<String> = None;
    let mut flux_key: Option<String> = None;
    for &(field, comp, name, elno) in MAP {
        let Some(key) = locate_key(fields, field) else { continue };
        let info = &fields[&key];
        if field == "DEPL" {
            depl_key = Some(key.clone());
        }
        if field == "FLUX_NOEU" {
            flux_key = Some(key.clone());
        }
        if info.steps.is_empty() {
            continue;
        }
        let step = &info.steps[0];
        if elno {
            let width = elno_width(step);
            if width == 0 || comp_index(info, comp, width).is_none() {
                continue;
            }
        } else {
            let width = nodal_width(step);
            if width == 0 || comp_index(info, comp, width).is_none() {
                continue;
            }
        }
        found.push((key, comp, name, elno));
    }
    let names: Vec<&str> = found.iter().map(|r| r.2).collect();
    if names.contains(&"displx") && names.contains(&"disply") && names.contains(&"displz") {
        if let Some(key) = depl_key {
            found.push((key, "MAG", "displmag", false));
        }
    }
    if names.contains(&"heatfluxx") && names.contains(&"heatfluxy") {
        if let Some(key) = flux_key {
            found.push((key, "MAG", "heatfluxmag", false));
        }
    }
    let mut vars = Vec::new();
    for (key, comp, name, elno) in found {
        let info = &fields[&key];
        if elno {
            vars.push(elno_var(name, info, comp, cells, model));
        } else {
            vars.push(nodal_var(name, info, comp, nodes));
        }
    }
    Ok(vars)
}

/// Code_Aster prefixes the result name, padded to 8 characters
/// (`res_____DEPL`). Shell results use NOM_RESU_MED the same way
/// (`res_sup_SIEQ_NOEU`). Tests use the plain name.
fn locate_key(fields: &HashMap<String, Field>, name: &str) -> Option<String> {
    if fields.contains_key(name) {
        return Some(name.to_string());
    }
    let mut hits: Vec<&str> = fields
        .keys()
        .filter(|k| k.len() > 8 && &k[8..] == name)
        .map(|k| k.as_str())
        .collect();
    let shell = ["res_sup_", "res_moy_", "res_inf_"];
    let plain: Vec<&str> = hits
        .iter()
        .copied()
        .filter(|k| !shell.iter().any(|p| k.starts_with(p)))
        .collect();
    let list: &[&str] = if plain.is_empty() { &hits } else { &plain };
    if !list.is_empty() {
        let mut owned: Vec<&str> = list.to_vec();
        owned.sort_unstable();
        return Some(owned[0].to_string());
    }
    let prefix = format!("{name:_<8}");
    let prefix = &prefix[..8];
    hits = fields
        .keys()
        .filter(|k| k.len() > 8 && k.starts_with(prefix))
        .map(|k| k.as_str())
        .collect();
    if hits.is_empty() {
        return None;
    }
    hits.sort_unstable();
    Some(hits[0].to_string())
}

fn wanted(name: &str) -> bool {
    if MAP.iter().any(|row| row.0 == name) {
        return true;
    }
    if name.len() > 8 && MAP.iter().any(|row| row.0 == &name[8..]) {
        return true;
    }
    let shell = ["res_sup_", "res_moy_", "res_inf_"];
    shell.iter().any(|p| name.starts_with(p))
}

fn nodal_width(step: &Step) -> usize {
    step.nodal.iter().find_map(|e| e.nodal.as_ref().map(|r| r.len())).unwrap_or(0)
}

fn elno_width(step: &Step) -> usize {
    for rows in step.elno.values() {
        for ent in rows {
            if let Some(points) = &ent.elno {
                if let Some(p) = points.first() {
                    return p.len();
                }
            }
        }
    }
    0
}

fn step_at(steps: &[Step], k: usize) -> &Step {
    if k < steps.len() {
        &steps[k]
    } else if steps.len() == 1 {
        &steps[0]
    } else {
        &steps[k.min(steps.len() - 1)]
    }
}

fn nodal_map(step: &Step, nodes: &[Node], info: &Field, comp: &str) -> HashMap<i32, f64> {
    let width = nodal_width(step);
    let mut out = HashMap::new();
    if comp == "MAG" {
        for (i, node) in nodes.iter().enumerate() {
            let Some(row) = step.nodal.get(i).and_then(|e| e.nodal.as_ref()) else { continue };
            if row.len() < 2 {
                continue;
            }
            let z = if row.len() > 2 { row[2] } else { 0.0 };
            out.insert(node.id, (row[0] * row[0] + row[1] * row[1] + z * z).sqrt());
        }
        return out;
    }
    let Some(idx) = comp_index(info, comp, width) else { return out };
    for (i, node) in nodes.iter().enumerate() {
        let Some(row) = step.nodal.get(i).and_then(|e| e.nodal.as_ref()) else { continue };
        if idx < row.len() {
            out.insert(node.id, row[idx]);
        }
    }
    out
}

fn nodal_var(name: &str, info: &Field, comp: &str, nodes: &[Node]) -> Var {
    let first = nodal_map(step_at(&info.steps, 0), nodes, info, comp);
    let mut ids: Vec<i32> = first.keys().copied().collect();
    ids.sort_unstable();
    let mut steps = Vec::with_capacity(info.steps.len());
    for k in 0..info.steps.len() {
        let map = if k == 0 {
            first.clone()
        } else {
            nodal_map(step_at(&info.steps, k), nodes, info, comp)
        };
        steps.push(ids.iter().map(|id| map.get(id).copied().unwrap_or(0.0)).collect());
    }
    Var {
        name: name.to_string(),
        elno: false,
        ids,
        steps,
        times: info.steps.iter().map(|s| s.time).collect(),
    }
}

fn elno_map(
    step: &Step,
    info: &Field,
    comp: &str,
    cells: &HashMap<String, Vec<Cell>>,
    model: Option<&scan::ModelMesh>,
) -> HashMap<i32, Vec<f64>> {
    let mut out = HashMap::new();
    for (typ, rows) in &step.elno {
        let Some(block) = cells.get(typ) else { continue };
        for (i, ent) in rows.iter().enumerate() {
            let Some(points) = &ent.elno else { continue };
            let Some(cell) = block.get(i) else { continue };
            let width = points.first().map(|p| p.len()).unwrap_or(0);
            let Some(idx) = comp_index(info, comp, width) else { continue };
            let mut by_node = HashMap::new();
            for (k, nid) in cell.nodes.iter().enumerate() {
                if k < points.len() && idx < points[k].len() {
                    by_node.insert(*nid, points[k][idx]);
                }
            }
            let order: Vec<i32> = model
                .and_then(|m| m.elements.get(&(cell.eid as u32)))
                .map(|ns| ns.iter().map(|n| *n as i32).collect())
                .unwrap_or_else(|| cell.nodes.clone());
            let values = order
                .iter()
                .map(|n| by_node.get(n).copied().unwrap_or(0.0))
                .collect();
            out.insert(cell.eid, values);
        }
    }
    out
}

fn elno_var(
    name: &str,
    info: &Field,
    comp: &str,
    cells: &HashMap<String, Vec<Cell>>,
    model: Option<&scan::ModelMesh>,
) -> Var {
    let first = elno_map(step_at(&info.steps, 0), info, comp, cells, model);
    let mut ids: Vec<i32> = first.keys().copied().collect();
    ids.sort_unstable();
    let mut steps = Vec::with_capacity(info.steps.len());
    for k in 0..info.steps.len() {
        let map = if k == 0 {
            first.clone()
        } else {
            elno_map(step_at(&info.steps, k), info, comp, cells, model)
        };
        let mut flat = Vec::new();
        for id in &ids {
            if let Some(v) = map.get(id) {
                flat.extend_from_slice(v);
            }
        }
        steps.push(flat);
    }
    Var {
        name: name.to_string(),
        elno: true,
        ids,
        steps,
        times: info.steps.iter().map(|s| s.time).collect(),
    }
}

fn write_xml(
    w: &mut impl Write,
    vars: &[Var],
    nodes: &[Node],
    model: Option<&scan::ModelMesh>,
) -> io::Result<()> {
    let nstep = vars.iter().map(|v| v.steps.len()).max().unwrap_or(1).max(1);
    let times = vars
        .iter()
        .find(|v| v.times.len() == nstep)
        .map(|v| v.times.clone())
        .unwrap_or_else(|| vec![0.0; nstep]);
    let static_case = nstep <= 1;
    let indent = if static_case { "      " } else { "        " };
    w.write_all(b"    <results precision=\"double\">\r\n")?;
    for var in vars {
        write_ids(w, var)?;
    }
    for k in 0..nstep {
        if !static_case {
            let t = times.get(k).copied().unwrap_or(0.0);
            write!(
                w,
                "      <timestep id=\"{k}\" time=\"{} s\">\r\n",
                py_g15(t)
            )?;
        }
        for var in vars {
            let Some(values) = var.steps.get(k).or_else(|| var.steps.first()) else { continue };
            write_var(w, var, values, nodes, model, indent)?;
        }
        if !static_case {
            w.write_all(b"      </timestep>\r\n")?;
        }
    }
    w.write_all(b"    </results>\r\n")?;
    Ok(())
}

fn write_ids(w: &mut impl Write, var: &Var) -> io::Result<()> {
    let tag = if var.elno { "elementnodeids" } else { "nodeids" };
    write!(w, "      <{tag} name=\"{}\">", xml_escape(&var.name))?;
    write_b64(w, &pack_i32(&var.ids))?;
    write!(w, "</{tag}>\r\n")?;
    Ok(())
}

fn write_var(
    w: &mut impl Write,
    var: &Var,
    values: &[f64],
    nodes: &[Node],
    model: Option<&scan::ModelMesh>,
    indent: &str,
) -> io::Result<()> {
    let tag = if var.elno { "elementnodevariable" } else { "nodevariable" };
    let empty = if var.elno { "elements" } else { "nodes" };
    let i1 = format!("{indent}  ");
    let i2 = format!("{indent}    ");
    write!(w, "{indent}<{tag} name=\"{}\">\r\n", xml_escape(&var.name))?;
    write!(w, "{i1}<maxandmin>\r\n")?;
    if var.elno {
        if !values.is_empty() {
            let (mn, mx) = min_max(values);
            write!(
                w,
                "{i2}<component name=\"\" max=\"{}\" min=\"{}\" />\r\n",
                py_g15(mx),
                py_g15(mn)
            )?;
        }
    } else {
        for (name, pos) in groups(var, nodes, model) {
            if pos.is_empty() {
                continue;
            }
            let sub: Vec<f64> = pos.iter().filter_map(|i| values.get(*i).copied()).collect();
            if sub.is_empty() {
                continue;
            }
            let (mn, mx) = min_max(&sub);
            write!(
                w,
                "{i2}<component name=\"{}\" max=\"{}\" min=\"{}\" />\r\n",
                xml_escape(&name),
                py_g15(mx),
                py_g15(mn)
            )?;
        }
    }
    write!(w, "{i1}</maxandmin>\r\n")?;
    write!(w, "{i1}<valuesdouble>")?;
    write_b64(w, &pack_f64(values))?;
    write!(
        w,
        "</valuesdouble>\r\n{i1}<{empty} />\r\n{i1}<values />\r\n{indent}</{tag}>\r\n"
    )?;
    Ok(())
}

fn groups(var: &Var, nodes: &[Node], model: Option<&scan::ModelMesh>) -> Vec<(String, Vec<usize>)> {
    let _ = nodes;
    let Some(model) = model else {
        return vec![("".to_string(), (0..var.ids.len()).collect())];
    };
    if model.elsets.is_empty() || model.elements.is_empty() {
        return vec![("".to_string(), (0..var.ids.len()).collect())];
    }
    let pos: HashMap<i32, usize> = var.ids.iter().enumerate().map(|(i, id)| (*id, i)).collect();
    let mut used = std::collections::HashSet::new();
    let mut groups = Vec::new();
    for (name, eids) in &model.elsets {
        let mut nids = Vec::new();
        for eid in eids {
            let Some(conn) = model.elements.get(eid) else { continue };
            for nid in conn {
                let nid = *nid as i32;
                if pos.contains_key(&nid) && !nids.contains(&nid) {
                    nids.push(nid);
                    used.insert(nid);
                }
            }
        }
        if !nids.is_empty() {
            groups.push((name.clone(), nids.iter().map(|n| pos[n]).collect()));
        }
    }
    let free: Vec<usize> = var
        .ids
        .iter()
        .filter(|n| !used.contains(n))
        .map(|n| pos[n])
        .collect();
    if !free.is_empty() {
        groups.insert(0, ("".to_string(), free));
    }
    if groups.is_empty() {
        vec![("".to_string(), (0..var.ids.len()).collect())]
    } else {
        groups
    }
}

fn min_max(values: &[f64]) -> (f64, f64) {
    let mut mn = values[0];
    let mut mx = values[0];
    for v in values.iter().skip(1) {
        if *v < mn {
            mn = *v;
        }
        if *v > mx {
            mx = *v;
        }
    }
    (mn, mx)
}

fn pack_i32(ids: &[i32]) -> Vec<u8> {
    let mut raw = Vec::with_capacity(ids.len() * 4);
    for id in ids {
        raw.extend_from_slice(&id.to_le_bytes());
    }
    raw
}

fn pack_f64(values: &[f64]) -> Vec<u8> {
    let mut raw = Vec::with_capacity(values.len() * 8);
    for v in values {
        raw.extend_from_slice(&v.to_le_bytes());
    }
    raw
}

fn write_b64(w: &mut impl Write, raw: &[u8]) -> io::Result<()> {
    const T: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut col = 0;
    let mut i = 0;
    while i < raw.len() {
        let b0 = raw[i];
        let b1 = if i + 1 < raw.len() { raw[i + 1] } else { 0 };
        let b2 = if i + 2 < raw.len() { raw[i + 2] } else { 0 };
        let n = ((b0 as u32) << 16) | ((b1 as u32) << 8) | b2 as u32;
        let mut chunk = [0u8; 4];
        chunk[0] = T[((n >> 18) & 63) as usize];
        chunk[1] = T[((n >> 12) & 63) as usize];
        chunk[2] = if i + 1 < raw.len() { T[((n >> 6) & 63) as usize] } else { b'=' };
        chunk[3] = if i + 2 < raw.len() { T[(n & 63) as usize] } else { b'=' };
        w.write_all(&chunk)?;
        col += 4;
        if col == 64 {
            w.write_all(b"\r\n")?;
            col = 0;
        }
        i += 3;
    }
    if col != 0 {
        w.write_all(b"\r\n")?;
    }
    Ok(())
}

fn xml_escape(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            _ => out.push(c),
        }
    }
    out
}

/// Python `"{0:.15G}".format(x)`, with 0 written as `0`.
fn py_g15(x: f64) -> String {
    if x == 0.0 {
        return "0".to_string();
    }
    let neg = x.is_sign_negative();
    let ax = x.abs();
    let exp = ax.log10().floor() as i32;
    let exp = if (ax / 10f64.powi(exp)) >= 10.0 { exp + 1 } else { exp };
    let sign = if neg { "-" } else { "" };
    if exp < -4 || exp >= 15 {
        let mant = ax / 10f64.powi(exp);
        let mut body = format!("{:.14}", mant);
        trim_plain(&mut body);
        return format!("{sign}{body}E{exp:+03}");
    }
    let frac = (14 - exp).max(0) as usize;
    let mut body = format!("{:.*}", frac, ax);
    trim_plain(&mut body);
    format!("{sign}{body}")
}

fn trim_plain(body: &mut String) {
    if body.contains('.') {
        while body.ends_with('0') {
            body.pop();
        }
        if body.ends_with('.') {
            body.pop();
        }
    }
}

fn comp_index(info: &Field, comp: &str, width: usize) -> Option<usize> {
    if let Some(i) = info.comps.iter().position(|c| c == comp) {
        return Some(i);
    }
    if comp == "MAG" {
        return None;
    }
    if info.comps.is_empty() {
        let idx = match comp {
            "DX" | "TEMP" | "VMIS" => 0,
            "DY" => 1,
            "DZ" => 2,
            _ => return None,
        };
        if idx < width { return Some(idx); }
    }
    None
}

fn fortran_f64(flat: &[f64], nrow: usize, ncol: usize) -> Vec<Vec<f64>> {
    (0..nrow)
        .map(|i| (0..ncol).map(|k| flat[i + k * nrow]).collect())
        .collect()
}

fn fortran_i64(flat: &[i64], nrow: usize, ncol: usize) -> Vec<Vec<i64>> {
    (0..nrow)
        .map(|i| (0..ncol).map(|k| flat[i + k * nrow]).collect())
        .collect()
}

fn read_ints(ds: &Dataset) -> io::Result<Vec<i64>> {
    if let Ok(v) = ds.read_i32() {
        return Ok(v.into_iter().map(|x| x as i64).collect());
    }
    if let Ok(v) = ds.read_i64() {
        return Ok(v);
    }
    if let Ok(v) = ds.read_u32() {
        return Ok(v.into_iter().map(|x| x as i64).collect());
    }
    ds.read_i16()
        .map(|v| v.into_iter().map(|x| x as i64).collect())
        .map_err(err)
}

fn read_opt_ints(ds: Result<Dataset, hdf5_pure::Error>) -> Option<Vec<i64>> {
    ds.ok().and_then(|d| read_ints(&d).ok())
}

fn components(raw: &str) -> Vec<String> {
    let raw = raw.trim_matches('\0');
    if raw.len() >= 16 && raw.len() % 16 == 0 {
        return raw
            .as_bytes()
            .chunks(16)
            .map(|c| String::from_utf8_lossy(c).trim().to_string())
            .collect();
    }
    if raw.is_empty() {
        return Vec::new();
    }
    raw.split_whitespace().map(|s| s.to_string()).collect()
}

fn attr_i64(ds: &Dataset, key: &str) -> Option<i64> {
    ds.attrs().ok()?.get(key)?.as_i64()
}

fn attr_i64_group(g: &Group, key: &str) -> Option<i64> {
    g.attrs().ok()?.get(key)?.as_i64()
}

fn attr_f64_group(g: &Group, key: &str) -> Option<f64> {
    let v = g.attrs().ok()?.get(key).cloned()?;
    if let Some(x) = v.as_f64() {
        return Some(x);
    }
    v.as_i64().map(|n| n as f64)
}

fn attr_text_group(g: &Group, key: &str) -> String {
    let Ok(attrs) = g.attrs() else { return String::new() };
    let Some(v) = attrs.get(key) else { return String::new() };
    attr_to_text(v)
}

fn attr_to_text(v: &AttrValue) -> String {
    if let Some(s) = v.as_str() {
        return s.trim_matches('\0').trim().to_string();
    }
    match v {
        AttrValue::U8Array(b) => String::from_utf8_lossy(b).trim_matches('\0').trim().to_string(),
        _ => String::new(),
    }
}
