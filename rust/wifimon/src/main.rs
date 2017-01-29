use std::io::prelude::*;
use std::fs::File;

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
    println!("{:?}", conf);

    let result = wifiscanner::scan();

    match result {
        Ok(networks) => {
            for wifi in networks {
                println!("{:?}: {:?} (known: {:?})", wifi.mac, wifi.ssid, haz(conf, &wifi));
            }
        },
        Err(_) => ()
    }
}
