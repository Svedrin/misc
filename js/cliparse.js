// CLI parser using a tree-like data structure to define commands,
// supporting command abbreviations.

function cli_parse(commands, line) {
    // https://github.com/Svedrin/misc/blob/master/js/cliparse.js
    // inner_parse function operates on a list of words
    function inner_parse(commands, words){
        if (words.length == 0 || words[0] == "?") {
            throw "Valid commands: " + Object.keys(commands).join(", ");
        }
        // Find candidates for the current command
        var candidates = (
            Object.keys(commands)
                .filter((candidate) => candidate.startsWith(words[0]))
        );
        console.log([commands, words[0], candidates]);
        if (candidates.length == 1) {
            // We're done if we found a function
            if (typeof commands[candidates[0]] == "function") {
                return [commands[candidates[0]], words.slice(1)];
            } else {
                // Parse the rest of the words with the commands from our
                // candidate
                return inner_parse(commands[candidates[0]], words.slice(1));
            }
        } else if (candidates.length == 0) {
            throw (
                `command not found: '${words[0]}', valid ones are: ` +
                Object.keys(commands).join(", ")
            );
        } else {
            throw (
                `command is ambiguous: '${words[0]}', candidates are: ` +
                candidates.join(", ")
            );
        }
    }
    // Split the command line and call inner_parse
    return inner_parse(commands, line.split(" "));
}


function test_cli_parse() {
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
    try {
        var fn, args;
        [fn, args] = cli_parse(commands, "xmas li on");
        fn(args);
    } catch(e) {
        console.log(e);
    }
}


module.exports = {cli_parse, test_cli_parse};
