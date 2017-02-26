use std::io::prelude::*;
use std::fs::File;
use std::collections::HashMap;

extern crate wifiscanner;
use wifiscanner::Wifi;

extern crate yaml_rust;
use yaml_rust::{YamlLoader,Yaml};

extern crate iron;
use iron::prelude::*;
use iron::status;
use iron::mime::{Mime,TopLevel,SubLevel};
use iron::headers::ContentType;

extern crate router;
use router::Router;

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
    if let Yaml::Array(ref aps) = conf["networks"][wifi.ssid.as_str()]["aps"] {
        for ap in aps {
            if *ap == Yaml::String(wifi.mac.clone()) {
                return Some(true);
            }
        }
    }
    return Some(false);
}


fn handle_index(_: &mut Request) -> IronResult<Response> {
    let mut resp = Response::with((status::Ok, r#"<h1>WifiMon</h1><a href="/metrics">Metrics</a>"#));
    resp.headers.set(ContentType(Mime(TopLevel::Text, SubLevel::Html, vec![])));
    Ok(resp)
}


fn handle_metrics(_: &mut Request) -> IronResult<Response> {
    let conf = match File::open("wifimon.conf") {
        Ok(mut f) => {
            let mut s = String::new();
            if let Err(err) = f.read_to_string(&mut s) {
                return Ok(Response::with((status::InternalServerError, format!("Failed to read wifimon.conf: {}", err))));
            }
            match YamlLoader::load_from_str(s.as_str()) {
                Ok(f)    => Some(f),
                Err(err) => return Ok(Response::with((status::InternalServerError, format!("Failed to parse wifimon.conf: {}", err))))
            }
        },
        Err(_) => None
    };

    let mut counters : HashMap<String, WifiAPCount> = HashMap::new();

    if let Ok(networks) = wifiscanner::scan() {
        for wifi in networks {
            if let Some(ref conf_) = conf {
                // If we have a config and it doesn't know this network, skip altogether
                if conf_[0]["networks"][wifi.ssid.as_str()] == Yaml::BadValue {
                    continue
                }
                // If the AP is known, count as known and be done
                if haz(&conf_[0], &wifi) == Some(true) {
                    counters.entry(wifi.ssid).or_insert(WifiAPCount::new())
                        .found_known();
                    continue;
                }
            }
            // No config or unknown AP, so count as unknown
            counters.entry(wifi.ssid).or_insert(WifiAPCount::new())
                .found_unknown();
        }
    }

    let mut result = vec!["# TYPE wifi_access_points gauge\n".to_string()];

    for (ssid, aps) in &counters {
        result.push(format!(r#"wifi_access_points{{ssid="{}",type="known"}} {}"#,   ssid, aps.known)   + "\n");
        result.push(format!(r#"wifi_access_points{{ssid="{}",type="unknown"}} {}"#, ssid, aps.unknown) + "\n");
    }

    Ok(Response::with((status::Ok, result.join(""))))
}

fn main() {
    // TODO: Move to
    // http://fengsp.github.io/pencil/pencil/

    let mut router = Router::new();

    router.get("/",        handle_index,   "index");
    router.get("/metrics", handle_metrics, "metrics");

    Iron::new(router).http("localhost:3000").unwrap();
}
