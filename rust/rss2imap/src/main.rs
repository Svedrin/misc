use std::env;
use std::fs::File;
use std::io::prelude::*;
use std::thread;

extern crate rss;
use rss::Channel;

extern crate yaml_rust;
use yaml_rust::{Yaml,YamlLoader};

extern crate openssl;
use openssl::ssl::{SslConnectorBuilder, SslMethod};

extern crate imap;
use imap::client::Client;

const CONTENT_TEMPLATE: &str =
r#"<div style="background-color: #ededed; border: 1px solid grey; margin: 5px;">
<table>
<tr><td><b>Feed:</b></td><td>{feed}</td></tr>
<tr><td><b>Item:</b></td><td><a href="{link}">{title}</td></tr>
</table>
</div>
{content}"#;



fn main() {
    let mut conffile = File::open(
        env::home_dir()
            .expect("Where's your homedir?")
            .join(".rss2imap.conf"))
        .expect("config file not found");

    let mut contents = String::new();
    conffile.read_to_string(&mut contents)
        .expect("could not read config file");

    let confs = YamlLoader::load_from_str(contents.as_str()).unwrap();
    if confs.len() < 1 {
        panic!("Conf is empty");
    }
    let conf = &confs[0];

    let imaphost = conf["imap"]["host"]
        .as_str()
        .expect("Imap host is not a string");
    let imapuser = conf["imap"]["user"]
        .as_str()
        .expect("Imap user is not a string");
    let imappass = conf["imap"]["pass"]
        .as_str()
        .expect("Imap pass is not a string");

    let mut imap_socket = Client::secure_connect(
        (&imaphost[..], 993),
        &imaphost[..],
        SslConnectorBuilder::new(SslMethod::tls())
            .unwrap()
            .build()
        )
        .expect("Could not connect to IMAP server");

    imap_socket.login(imapuser, imappass)
        .expect("Imap login failed");

    let mut children = vec![];

    for (imapdir, feeds) in conf["feeds"]
        .as_hash()
        .expect("feeds is not a dict")
    {
        let dirname = imapdir
            .as_str()
            .expect("dirname is not a string")
            .clone()
            .to_owned();

        for (_feedname, feedconf) in feeds
            .as_hash()
            .expect(format!("config for {} is not a dict", dirname).as_str())
        {
            let feedname = _feedname
                .as_str()
                .expect("feedname is not a string")
                .clone()
                .to_owned();
            let feedurl =
                match feedconf {
                    &Yaml::String(ref url) => Some(url.as_str()),
                    &Yaml::Hash(_) => Some(feedconf["url"]
                        .as_str()
                        .expect(format!("config for feed {} does not have a url string", feedname).as_str())),
                    _ => None
                }
                .expect(format!("config for feed {} is not a string or hash", feedname).as_str())
                .clone()
                .to_owned();

            let dirname = dirname.clone();

            children.push(
                thread::Builder::new()
                    .name(feedname.clone())
                    .spawn(move || {
                        let channel = Channel::from_url(&feedurl).unwrap();
                        for item in channel.items().iter() {
                            println!("{:?} -> {:?}", dirname,
                                CONTENT_TEMPLATE
                                    .replace("{feed}",    feedname.as_str())
                                    .replace("{title}",   item.title().unwrap_or_else(|| "no title"))
                                    .replace("{link}",    item.link().unwrap_or_else(|| "no link"))
                                    .replace("{content}", item.description().unwrap_or_else(|| "no content"))
                            );
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


}
