use std::io::prelude::*;
use std::fs::File;
use std::collections::HashMap;

extern crate wifiscanner;
use wifiscanner::Wifi;

extern crate yaml_rust;
use yaml_rust::{YamlLoader,Yaml};


#[derive(Hash, Eq, PartialEq, Debug)]
struct WifiAPCount {
    known:   i32,
    unknown: i32
}

impl WifiAPCount {
    fn new() -> WifiAPCount {
        WifiAPCount { known: 0, unknown: 0 }
    }

    fn found_known(&mut self) {
        self.known += 1;
    }

    fn found_unknown(&mut self) {
        self.unknown += 1;
    }
}


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

    let mut counters : HashMap<String, WifiAPCount> = HashMap::new();

    match wifiscanner::scan() {
        Ok(networks) => {
            for wifi in networks {
//                 println!("{:?}: {:?} (known: {:?})", wifi.mac, wifi.ssid, haz(conf, &wifi));
                match haz(conf, &wifi) {
                    Some(true)  => {
                        counters.entry(wifi.ssid).or_insert(WifiAPCount::new())
                            .found_known();
                    }
                    Some(false) => {
                        counters.entry(wifi.ssid).or_insert(WifiAPCount::new())
                            .found_unknown();
                    }
                    None => ()
                };
            }
        },
        Err(_) => ()
    }

    println!("# TYPE wifi_access_points gauge");

    for (ssid, aps) in &counters {
        println!("wifi_access_points{{ssid=\"{}\",type=\"known\"}} {}",   ssid, aps.known);
        println!("wifi_access_points{{ssid=\"{}\",type=\"unknown\"}} {}", ssid, aps.unknown);
    }
}
