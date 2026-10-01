//! Sözcüksel (Lexical) Seviye Mutatörler

use super::Mutator;
use rand::prelude::*;

pub struct CaseToggleMutator;

impl Mutator for CaseToggleMutator {
    fn name(&self) -> &'static str {
        "lexical::case_toggle"
    }

    fn mutate(&self, input: &str) -> String {
        let mut rng = thread_rng();
        input
            .chars()
            .map(|c| {
                if c.is_alphabetic() && rng.gen_bool(0.3) {
                    if c.is_uppercase() {
                        c.to_lowercase().to_string()
                    } else {
                        c.to_uppercase().to_string()
                    }
                } else {
                    c.to_string()
                }
            })
            .collect()
    }
}

pub struct ZeroWidthInjector;

impl Mutator for ZeroWidthInjector {
    fn name(&self) -> &'static str {
        "lexical::zero_width_injector"
    }

    fn mutate(&self, input: &str) -> String {
        let mut rng = thread_rng();
        let zw_chars = ['\u{200B}', '\u{200C}', '\u{200D}', '\u{FEFF}'];
        let mut result = String::with_capacity(input.len() * 2);

        for c in input.chars() {
            result.push(c);
            if rng.gen_bool(0.15) {
                if let Some(&zw) = zw_chars.choose(&mut rng) {
                    result.push(zw);
                }
            }
        }
        result
    }
}

pub struct HomoglyphMutator;

impl Mutator for HomoglyphMutator {
    fn name(&self) -> &'static str {
        "lexical::homoglyph"
    }

    fn mutate(&self, input: &str) -> String {
        let mut rng = thread_rng();
        input
            .chars()
            .map(|c| {
                if rng.gen_bool(0.25) {
                    match c {
                        'a' => 'а', // Cyrillic Small Letter A
                        'c' => 'с', // Cyrillic Small Letter Es
                        'e' => 'е', // Cyrillic Small Letter Ie
                        'i' => 'і', // Cyrillic Small Letter Byelorussian-Ukrainian I
                        'j' => 'ј', // Cyrillic Small Letter Je
                        'o' => 'о', // Cyrillic Small Letter O
                        'p' => 'р', // Cyrillic Small Letter Er
                        's' => 'ѕ', // Cyrillic Small Letter Dze
                        'x' => 'х', // Cyrillic Small Letter Ha
                        'y' => 'у', // Cyrillic Small Letter U
                        _ => c,
                    }
                } else {
                    c
                }
            })
            .collect()
    }
}

pub struct WhitespaceMutator;

impl Mutator for WhitespaceMutator {
    fn name(&self) -> &'static str {
        "lexical::whitespace_shuffle"
    }

    fn mutate(&self, input: &str) -> String {
        let mut rng = thread_rng();
        let variants = ["  ", "   ", "\t", " \t ", "\n"];
        let mut result = String::with_capacity(input.len() + 32);

        for c in input.chars() {
            if c == ' ' && rng.gen_bool(0.3) {
                let choice = variants.choose(&mut rng).unwrap_or(&" ");
                result.push_str(choice);
            } else {
                result.push(c);
            }
        }
        result
    }
}
