// CLI parser using a tree-like data structure to define commands,
// supporting command abbreviations.

function cli_parse(commands, line) {
    // inner_parse function operates on a list of words
    function inner_parse(commands, words){
        // Find candidates for the current command
        var candidates = (
            Object.keys(commands)
                .filter((candidate) => candidate.startsWith(words[0]))
        );
        console.log([commands, words[0], candidates]);
        if (candidates.length == 1) {
            // We're done if we found a function
            if (typeof commands[candidates[0]] == "function") {
                return commands[candidates[0]];
            } else {
                // Parse the rest of the words with the commands from our
                // candidate
                return inner_parse(commands[candidates[0]], words.slice(1));
            }
        } else if (candidates.length == 0) {
            throw "command not found: " + words[0];
        } else {
            throw [
                "command is ambiguous: '",
                words[0],
                "' candidates are: ",
                candidates.join(", ")
            ].join("");
        }
    }
    // Split the command line and call inner_parse
    return inner_parse(commands, line.split(" "));
}


function test() {
    commands = {
        xmas: {
            lights: {
                on () {
                    console.log("on");
                },
                off () {
                    console.log("off");
                }
            },
            lovers () {
                console.log("<3");
            }
        }
    }
    fn = cli_parse(commands, "xmas li on");
    fn();
}

try {
    test();
} catch(e) {
    console.log(e);
}
