extern crate crossbeam;
extern crate hyper;
extern crate imap;
extern crate mime_multipart;
extern crate openssl;
extern crate rss;
extern crate sha1;
extern crate yaml_rust;

use std::env;
use std::fs::File;
use std::io::prelude::*;
use std::io::{Cursor,SeekFrom};
use hyper::header::Headers;
use rss::Channel;
use imap::client::Client;
use mime_multipart::{Node,Part,write_multipart,generate_boundary};
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


fn hash_id(item: &rss::Item) -> Option<String> {
    if let Some(guid) = item.guid() {
        let sha = &mut sha1::Sha1::new();
        sha.update(guid.value().as_bytes());
        Some(sha.digest().to_string())
    } else {
        None
    }
}

fn build_headers(headers: Vec<(String, String)>) -> Headers {
    let mut hdrs = Headers::new();
    for (header, value) in headers {
        hdrs.append_raw(header, value.into_bytes());
    }
    return hdrs;
}

fn build_email(feedname: &str, item: &rss::Item) -> Result<String, String> {
    /**
     * MIME Structure:
     *
     *  multipart/related
     *  + multipart/alternative
     *  | + text/html
     *  + image/png
     *  + image/jpg
     *  + ...
     *
     * The multipart/alternative seems superfluous, but (at least)
     * Thunderbird doesn't render the email correctly without it.
     */

    let node = Node::Multipart((build_headers(vec![
        (
            "Content-Type".to_string(),
            format!("multipart/related; boundary=\"{}\"",
                String::from_utf8(generate_boundary())
                    .map_err(|err| err.to_string())?).to_string()
        ),
        ("From".to_string(),          feedname.to_string()),
        ("Subject".to_string(),       item.title().unwrap_or("no title").to_string()),
        ("X-RSS2IMAP-ID".to_string(), hash_id(item).unwrap_or("no ID".to_string())),
        ("Date".to_string(),          "TODO".to_string()),
    ]), vec![
        Node::Multipart((build_headers(vec![
            (
                "Content-Type".to_string(),
                format!("multipart/alternative; boundary=\"{}\"",
                        String::from_utf8(generate_boundary())
                            .map_err(|err| err.to_string())?).to_string()
            )
        ]), vec![
            Node::Part(Part {
                headers: build_headers(vec![
                    ("Content-Type".to_string(), "text/html; charset=\"utf-8\"".to_string())
                ]),
                body: CONTENT_TEMPLATE
                    .replace("{feed}",    feedname)
                    .replace("{title}",   item.title().unwrap_or("no title"))
                    .replace("{link}",    item.link().unwrap_or("no link"))
                    .replace("{content}", item.description().unwrap_or("no content"))
                    .into_bytes()
            } )
        ]))
    ]));

    let mut stream = Cursor::new(vec![0; 4096]);
    let mut result = String::new();
    write_multipart(&mut stream, &vec![], &vec![node])
        .map_err(|err| err.to_string())?;
    // write_multipart puts in one boundary too many, so strip leading --\r\n by seeking to 4, ...
    stream.seek(SeekFrom::Start(4))
        .map_err(|err| err.to_string())?;
    stream.read_to_string(&mut result)
        .map_err(|err| err.to_string())?;
    Ok(
        result.trim_right_matches('\0')
            .trim_right_matches('-')      // ... and strip trailing ---- by using trim.
            .to_string()
    )
}

fn run() -> Result<(), String> {
    let conffile = &mut String::new();
    File::open(
        env::home_dir()
            .ok_or("Where's your homedir?")?
            .join(".rss2imap.conf")
        )
        .map_err(|err| format!("Could not open config file [~/.rss2imap.conf]: {}", err))?
        .read_to_string(conffile)
        .map_err(|err| format!("Could not read config file [~/.rss2imap.conf]: {}", err))?;

    let confs = YamlLoader::load_from_str(conffile.as_str())
        .map_err(|err| format!("Config is not valid YAML: {}", err))?;
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

    let imap_socket = &mut Client::secure_connect(
        (&imaphost[..], 993),
        &imaphost[..],
        SslConnectorBuilder::new(SslMethod::tls())
            .unwrap()
            .build()
        )
        .map_err(|err| format!("Could not connect to IMAP server: {}", err))?;

    imap_socket.login(imapuser, imappass)
        .map_err(|err| format!("Imap login failed: {}", err))?;

    let jobs = &mut vec![];

    for (imapdir, feeds) in conf["feeds"]
        .as_hash()
        .ok_or("feeds is not a dict")?
    {
        let dirname = imapdir
            .as_str()
            .ok_or("dirname is not a string")?;

        for (_feedname, feedconf) in feeds
            .as_hash()
            .ok_or(format!("config for {} is not a dict", dirname).as_str())?
        {
            let feedname = _feedname
                .as_str()
                .ok_or("feedname is not a string")?;

            let feedurl =
                match feedconf {
                    &Yaml::String(ref url) => Some(url.as_str()),
                    &Yaml::Hash(_) => Some(feedconf["url"]
                        .as_str()
                        .ok_or(format!("config for feed {} does not have a url string", feedname))?),
                    _ => None
                }
                .ok_or(format!("config for feed {} is not a string or hash", feedname))?;

            jobs.push( (dirname, feedname, feedurl) );
        }
    }

    crossbeam::scope(|scope| {
        for (dirname, feedname, feedurl) in jobs.drain(..) {
            scope.spawn(move || {
                let channel = match Channel::from_url(&feedurl) {
                    Ok(chan) => chan,
                    Err(err) => {
                        println!("{} -> {} failed to parse: {}", dirname, feedname, err);
                        return;
                    }
                };
                for item in channel.items().iter() {
                    println!("{} -> {}: {:?}", dirname, feedname,
                        build_email(&feedname, item).unwrap());
                    return;
                }
            });
        }
    });

    Ok(())
}

fn main() {
    if let Err(err) = run() {
        println!("Error: {}", err);
    }
}
