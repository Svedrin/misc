<#
.SYNOPSIS
    Run LaTeX-enabled pandoc in a Docker container in the local directory.
.DESCRIPTION
    Finally u can haz pandoc on Windows!
    .
    Backslashes are converted into forward slashes before running pandoc so that you can use tab completion.
.EXAMPLE
    .\run-pandoc.ps1 .\document.md -o document.pdf
.EXAMPLE
    .\run-pandoc.ps1 --pdf-engine=xelatex -t beamer .\presentation.md -o .\presentation.pdf
#>

$args_without_backslash = @()

foreach ($arg in $args) {
    $args_without_backslash += $arg.replace("\", "/")
}

docker run --rm -it -v ($PWD.Path + ":/data") -w /data pandoc/latex:latest ($args_without_backslash)
