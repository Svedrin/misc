package main

import (
	"bytes"
	"crypto/sha1"
	"encoding/base64"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"strings"
	"mime/multipart"
	"net/http"
	"net/textproto"
	//"github.com/martine/go-imap/src/imap"
	"github.com/iand/feedparser"
	"code.google.com/p/go.net/html"
)

const content_template = `
<div style="background-color: #ededed; border: 1px solid grey; margin: 5px;">
    <table>
        <tr><td><b>Feed:</b></td><td>%s</td></tr>
        <tr><td><b>Item:</b></td><td><a href="%s">%s</td></tr>
    </table>
</div>
`

func get_content_id(url string) string {
	sha1 := sha1.New()
	io.WriteString(sha1, url)
	return fmt.Sprintf("%x", sha1.Sum(nil))
}

type Resource struct{
	Header textproto.MIMEHeader;
	Content io.Reader;
}

func get_resource(channel chan Resource, url string) {
	res, err := http.Get(url)
	if err != nil {
		log.Fatal(err)
	}
	
	header := make(textproto.MIMEHeader)
	header.Set("Content-Type", res.Header.Get("Content-Type"))
	header.Set("Content-ID",   fmt.Sprintf("<%s>", get_content_id(url)))
	header.Set("X-IMG-SRC",    url)
	
	content := new(bytes.Buffer)
	
	if res.Header.Get("Content-Type")[:5] != "text/" {
		header.Set("Content-Transfer-Encoding", "base64")
		encoder := base64.NewEncoder(base64.StdEncoding, content)
		data, _ := ioutil.ReadAll(res.Body)
		encoder.Write(data)
		encoder.Close()
	} else {
		io.Copy(content, res.Body)
	}
	
	res.Body.Close()
	channel <- Resource{header, content}
}

func get_feed_item(readyc chan bool, feedname string, item *feedparser.FeedItem) {
	resourcec := make(chan Resource)
	body   := new(bytes.Buffer)
	writer := multipart.NewWriter(body)
	
	// MIME Structure:
	//
	//  multipart/related
	//  + multipart/alternative
	//  | + text/html
	//  + image/png
	//  + image/jpg
	//  + ...
	//
	// The multipart/alternative seems superfluous, but (at least)
	// Thunderbird doesn't render the email correctly without it.
	
	fmt.Printf("From: %s\n", feedname)
	fmt.Printf("Subject: %s\n", item.Title)
	fmt.Printf("X-RSS2IMAP-ID: %s\n", get_content_id(item.Id))
	fmt.Printf("Content-Type: multipart/related;  boundary=\"%s\"\n", writer.Boundary())
	fmt.Printf("\n")
	
	altbody   := new(bytes.Buffer)
	altwriter := multipart.NewWriter(altbody)
	altheader := make(textproto.MIMEHeader)
	altheader.Set("Content-Type", fmt.Sprintf("multipart/alternative;  boundary=\"%s\"", altwriter.Boundary()))
	
	cntheader := make(textproto.MIMEHeader)
	cntheader.Set("Content-Type", "text/html")
	cntpart, _ := altwriter.CreatePart(cntheader)
	
	// Parse the item's content for images.
	outstanding := 0
	buf := new(bytes.Buffer)
	io.WriteString(buf, item.Description)
	tkz := html.NewTokenizer(buf)
	
	io.WriteString(cntpart, fmt.Sprintf(content_template, feedname, item.Link, item.Title))
	
	Parse: for {
		switch tkz.Next() {
		case html.ErrorToken:
			// Returning io.EOF indicates success.
			break Parse
		case html.StartTagToken, html.SelfClosingTagToken:
			token := tkz.Token()
			if token.Data == "img" {
				for attr := range token.Attr {
					url := token.Attr[attr].Val
					if token.Attr[attr].Key == "src" {
						if strings.Contains(url, "doubleclick.") {
							continue Parse
						}
						if strings.Contains(url, "feedsportal.com") {
							continue Parse
						}
						go get_resource(resourcec, url)
						outstanding++
						io.WriteString(cntpart, fmt.Sprintf("<img src=\"cid:%s\"></img>", get_content_id(url)))
						continue Parse
					}
				}
			} else {
				io.WriteString(cntpart, token.String())
			}
		default:
			io.WriteString(cntpart, tkz.Token().String())
		}
	}
	
	altwriter.Close()
	
	altpart, _ := writer.CreatePart(altheader)
	io.Copy(altpart, altbody)
	
	for outstanding > 0 {
		resource := <-resourcec
		part, err := writer.CreatePart(resource.Header)
		if err != nil {
			log.Fatal(err)
		}
		
		_, err = io.Copy(part, resource.Content)
		outstanding--
	}
	
	writer.Close()
	fmt.Printf("%s", body)
	readyc <- true
}

func get_feed(readyc chan bool, url string) {
	itemreadyc := make(chan bool)
	outstanding := 0
	
	feedres, err := http.Get(url)
	if err != nil {
		log.Fatal(err)
	}
	
	feed, _ := feedparser.NewFeed(feedres.Body)
	
	for feeditem := range feed.Items {
// 		fmt.Printf("%s\n", feed.Items[feeditem].Description)
		go get_feed_item(itemreadyc, feed.Title, feed.Items[feeditem])
		outstanding++
		break
	}
	for outstanding > 0 {
		<-itemreadyc
		outstanding--
	}
	readyc <- true
}

func main() {
	feedreadyc := make(chan bool)
	go get_feed(feedreadyc, "http://www.questionablecontent.net/QCRSS.xml")
	<-feedreadyc
}
