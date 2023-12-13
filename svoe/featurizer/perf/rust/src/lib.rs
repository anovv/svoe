use pyo3::prelude::*;
use std::collections::HashMap;
use std::collections::VecDeque;

/// for JIT compile https://charlycst.github.io/posts/jit-ing-rust/

/// Formats the sum of two numbers as string.
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

#[pyfunction]
fn sum_list_dicts(a: Vec<HashMap<String, i32>>, key: String) -> PyResult<i32> {
    let mut tot = 0_i32;

    for d in a.iter() {
        tot += d[&key];
    }
    Ok(tot)
}

#[pyfunction]
fn sum_tuples(a: Vec<(i32, i32)>) -> PyResult<i32> {
    let mut tot = 0_i32;

    for d in a.iter() {
        tot += d.0;
        tot += d.1;
    }
    Ok(tot)
}

/// (id, timestamp, amount, price, side)
#[pyfunction]
fn calc_tvi(trades: Vec<(String, f32, f32, f32, String)>, window_s: f32) -> PyResult<Vec<(f32, f32)>> {
    let mut deque: VecDeque<&(String, f32, f32, f32, String)> = VecDeque::new();

    let mut res = vec![];
    for e in trades.iter() {
        deque.push_back(e);
        while e.1 - deque.get(0).unwrap().1 > window_s {
            deque.pop_front();
        }

        let mut buys_vol = 0_f32;
        let mut sells_vol = 0_f32;
        for t in deque.iter() {
            if "BUY".eq(&(t.4)) {
                buys_vol += t.2 * t.3;
            } else {
                sells_vol += t.2 * t.3;
            }
        }
        let tvi = 2.0 * (buys_vol - sells_vol)  / (buys_vol + sells_vol);

        res.push((e.1, tvi))
    }

    Ok(res)
}

/// (id, timestamp, amount, price, side)
#[pyfunction]
fn calc_tvi_fast(trades: Vec<(String, f32, f32, f32, String)>, window_s: f32) -> PyResult<Vec<(f32, f32)>> {
    let mut deque: VecDeque<&(String, f32, f32, f32, String)> = VecDeque::new();
    let mut sells_vol = 0_f32;
    let mut buys_vol = 0_f32;

    let mut res = vec![];
    for e in trades.iter() {
        deque.push_back(e);
        if "BUY".eq(&(e.4)) {
            buys_vol += e.2 * e.3;
        } else {
            sells_vol += e.2 * e.3;
        }
        while e.1 - deque.get(0).unwrap().1 > window_s {
            let front_e = deque.pop_front().unwrap();
            if "BUY".eq(&(front_e.4)) {
                buys_vol -= front_e.2 * front_e.3;
            } else {
                sells_vol -= front_e.2 * front_e.3;
            }
        }
        let tvi = 2.0 * (buys_vol - sells_vol)  / (buys_vol + sells_vol);

        res.push((e.1, tvi))
    }

    Ok(res)
}

/// A Python module implemented in Rust.
#[pymodule]
fn svoe_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_function(wrap_pyfunction!(sum_list_dicts, m)?)?;
    m.add_function(wrap_pyfunction!(sum_tuples, m)?)?;
    m.add_function(wrap_pyfunction!(calc_tvi, m)?)?;
    m.add_function(wrap_pyfunction!(calc_tvi_fast, m)?)?;
    Ok(())
}