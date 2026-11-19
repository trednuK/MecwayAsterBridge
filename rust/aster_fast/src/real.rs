//! Python ``"%.15g" % value`` plus the decimal point ``_real`` adds.
//! Rust's ``{:.14e}`` is 15 significant digits; the rest is the same
//! choice between fixed and scientific form as CPython's ``g``.

pub fn real(value: f64) -> String {
    let raw = g15(value);
    if raw.contains('.') || raw.contains('n') {
        return raw;
    }
    if let Some(e) = raw.find('e') {
        let mut out = String::with_capacity(raw.len() + 2);
        out.push_str(&raw[..e]);
        out.push_str(".0");
        out.push_str(&raw[e..]);
        out
    } else {
        let mut out = raw;
        out.push_str(".0");
        out
    }
}

fn g15(value: f64) -> String {
    if value.is_nan() {
        return "nan".to_string();
    }
    if value.is_infinite() {
        return if value.is_sign_negative() {
            "-inf".to_string()
        } else {
            "inf".to_string()
        };
    }
    if value == 0.0 {
        return if value.is_sign_negative() {
            "-0".to_string()
        } else {
            "0".to_string()
        };
    }
    let neg = value.is_sign_negative();
    let sci = format!("{:.14e}", value.abs());
    let mut body = g15_from_sci(&sci);
    if neg {
        body.insert(0, '-');
    }
    body
}

/// `sci` is Rust `{:.14e}` of a positive finite number, e.g. `1.2300e4`.
fn g15_from_sci(sci: &str) -> String {
    let (mant, exp_s) = sci.split_once('e').expect("scientific form");
    let exp: i32 = exp_s.parse().expect("exponent");
    let mut digits = String::with_capacity(16);
    for c in mant.chars() {
        if c != '.' {
            digits.push(c);
        }
    }
    while digits.len() > 1 && digits.ends_with('0') {
        digits.pop();
    }
    if exp < -4 || exp >= 15 {
        let mut m = String::new();
        m.push(digits.chars().next().unwrap_or('0'));
        let rest: String = digits.chars().skip(1).collect();
        if !rest.is_empty() {
            m.push('.');
            m.push_str(&rest);
        }
        return format!("{}e{:+03}", m, exp);
    }
    if exp >= 0 {
        let pos = exp as usize + 1;
        if digits.len() <= pos {
            let mut s = digits;
            while s.len() < pos {
                s.push('0');
            }
            s
        } else {
            let mut s = String::new();
            s.push_str(&digits[..pos]);
            s.push('.');
            s.push_str(&digits[pos..]);
            s
        }
    } else {
        let mut s = String::from("0.");
        for _ in 0..(-exp - 1) {
            s.push('0');
        }
        s.push_str(&digits);
        s
    }
}

#[cfg(test)]
mod tests {
    use super::real;

    #[test]
    fn matches_python_samples() {
        let cases = [
            (0.0, "0.0"),
            (-0.0, "-0.0"),
            (1.0, "1.0"),
            (-1.0, "-1.0"),
            (0.1, "0.1"),
            (1e-4, "0.0001"),
            (1e-5, "1.0e-05"),
            (-1e-5, "-1.0e-05"),
            (1e15, "1.0e+15"),
            (1e16, "1.0e+16"),
            (1.25, "1.25"),
            (std::f64::consts::PI, "3.14159265358979"),
            (1e20, "1.0e+20"),
            (-3.5, "-3.5"),
            (9999999.0, "9999999.0"),
            (10.0, "10.0"),
            (9.99e-5, "9.99e-05"),
        ];
        for (value, expect) in cases {
            assert_eq!(real(value), expect, "value {value}");
        }
    }
}
