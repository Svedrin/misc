extern crate imap;
extern crate openssl;
extern crate rss;
extern crate yaml_rust;

use std::env;
use std::fs::File;
use std::io::prelude::*;
use std::thread;
use rss::Channel;
use imap::client::Client;
use openssl::ssl::{SslConnectorBuilder, SslMethod};
use yaml_rust::{Yaml,YamlLoader};

const CONTENT_TEMPLATE: &str =
r#"<div style="background-color: #ededed; border: 1px solid grey; margin: 5px;">
<table>
<tr><td><b>Feed:</b></td><td>{feed}</td></tr>
<tr><td><b>Item:</b></td><td><a href="{link}">{title}</td></tr>
</table>
</div>
{content}"#;


fn run() -> Result<(), String> {
    let mut conffile = File::open(
        env::home_dir()
            .ok_or("Where's your homedir?")?
            .join(".rss2imap.conf")
        )
        .ok()
        .ok_or("Config file ~/.rss2imap.conf not found")?;

    let mut contents = String::new();
    conffile.read_to_string(&mut contents)
        .expect("could not read config file");

    let confs = YamlLoader::load_from_str(contents.as_str()).unwrap();
    if confs.len() < 1 {
        return Err(String::from("Conf is empty"));
    }
    let conf = &confs[0];

    let imaphost = conf["imap"]["host"]
        .as_str()
        .ok_or("Imap host is not a string")?;
    let imapuser = conf["imap"]["user"]
        .as_str()
        .ok_or("Imap user is not a string")?;
    let imappass = conf["imap"]["pass"]
        .as_str()
        .ok_or("Imap pass is not a string")?;

    let mut imap_socket = Client::secure_connect(
        (&imaphost[..], 993),
        &imaphost[..],
        SslConnectorBuilder::new(SslMethod::tls())
            .unwrap()
            .build()
        )
        .ok()
        .ok_or("Could not connect to IMAP server")?;

    imap_socket.login(imapuser, imappass)
        .ok()
        .ok_or("Imap login failed")?;

    let mut children = vec![];

    for (imapdir, feeds) in conf["feeds"]
        .as_hash()
        .ok_or("feeds is not a dict")?
    {
        let dirname = imapdir
            .as_str()
            .ok_or("dirname is not a string")?
            .clone()
            .to_owned();

        for (_feedname, feedconf) in feeds
            .as_hash()
            .ok_or(format!("config for {} is not a dict", dirname).as_str())?
        {
            let feedname = _feedname
                .as_str()
                .ok_or("feedname is not a string")?
                .clone()
                .to_owned();
            let feedurl =
                match feedconf {
                    &Yaml::String(ref url) => Some(url.as_str()),
                    &Yaml::Hash(_) => Some(feedconf["url"]
                        .as_str()
                        .ok_or(format!("config for feed {} does not have a url string", feedname))?),
                    _ => None
                }
                .ok_or(format!("config for feed {} is not a string or hash", feedname))?
                .clone()
                .to_owned();

            let dirname = dirname.clone();

            children.push(
                thread::Builder::new()
                    .name(feedname.clone())
                    .spawn(move || {
                        let channel = match Channel::from_url(&feedurl) {
                            Ok(chan) => chan,
                            Err(err) => {
                                println!("Error parsing feed {}: {}", feedname, err);
                                return;
                            }
                        };
                        for item in channel.items().iter() {
                            println!("{:?} -> {:?}", dirname,
                                CONTENT_TEMPLATE
                                    .replace("{feed}",    feedname.as_str())
                                    .replace("{title}",   item.title().unwrap_or("no title"))
                                    .replace("{link}",    item.link().unwrap_or("no link"))
                                    .replace("{content}", item.description().unwrap_or("no content"))
                            );
                            return;
                        }
                    })
                    .expect(format!("Could not start parser thread for feed {:?}", _feedname).as_str())
            );
        }
    }

    for child in children {
        // Wait for the thread to finish. Returns a result.
        let _ = child.join();
    }

    Ok(())
}

fn main() {
    if let Err(err) = run() {
        println!("Error: {}", err);
    }
}
