use std::io::prelude::*;
use std::fs::File;
use std::collections::HashMap;

extern crate wifiscanner;
use wifiscanner::Wifi;

extern crate yaml_rust;
use yaml_rust::{YamlLoader,Yaml};


fn haz(conf: &Yaml, wifi: &Wifi) -> Option<bool> {
    match conf["networks"][wifi.ssid.as_str()]["aps"] {
        Yaml::Array(ref aps) => {
            for ap in aps {
                if match ap {
                    &Yaml::String(ref v) => *v == wifi.mac,
                    _ => false
                } {
                    return Some(true);
                }
            }
            return Some(false);
        },
        _ => return None
    };
}

fn main() {
    let mut f = File::open("wifimon.conf").unwrap();
    let mut s = String::new();
    f.read_to_string(&mut s).unwrap();
    let conf_wat = YamlLoader::load_from_str(s.as_str()).unwrap();
    let conf = &conf_wat[0];
//     println!("{:?}", conf);

    let mut counters_known   : HashMap<String, i32> = HashMap::new();
    let mut counters_unknown : HashMap<String, i32> = HashMap::new();

    match wifiscanner::scan() {
        Ok(networks) => {
            for wifi in networks {
//                 println!("{:?}: {:?} (known: {:?})", wifi.mac, wifi.ssid, haz(conf, &wifi));
                match haz(conf, &wifi) {
                    Some(true)  => {
                        let x = match counters_known.get(&wifi.ssid) {
                            Some(x) => x + 1,
                            None    => 1
                        };
                        counters_known.insert(wifi.ssid.clone(), x);
                    }
                    Some(false) => {
                        let x = match counters_unknown.get(&wifi.ssid) {
                            Some(x) => x + 1,
                            None    => 1
                        };
                        counters_unknown.insert(wifi.ssid.clone(), x);
                    }
                    None => ()
                };
            }
        },
        Err(_) => ()
    }

    println!("# TYPE wifi_access_points gauge");

    match conf["networks"] {
        Yaml::Hash(ref networks) => {
            for yamlkey in networks.keys() {
                match yamlkey {
                    &Yaml::String(ref key) => {
                        println!("wifi_access_points{{ssid=\"{}\",type=\"known\"}} {}", key, match counters_known.get(key) {
                            Some(x) => *x,
                            None => 0
                        });
                        println!("wifi_access_points{{ssid=\"{}\",type=\"unknown\"}} {}", key, match counters_unknown.get(key) {
                            Some(x) => *x,
                            None => 0
                        });
                    },
                    _ => ()
                }
            }
        }
        _ => ()
    }
}
