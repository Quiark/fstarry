# F\* interactive proving for Neovim #

This is a python3 based plugin that brings the interactive proving capability to Neovim. 
Currently it supports pushing blocks of code to F\*, displaying errors in the quickfix window,
popping blocks back out and looking up symbols. Symbol autocomplete may be added later,
syntastic integration is not planned.

## Status ##

Very alpha. But I'm already using it.

## Not a neovim user? ##

Give it a try, it's stable and as compatible with Vim as possible.

## Installation ##

Should be pretty standard, use your package manager and then run `:UpdateRemotePlugins`
to refresh the definitions cache. Requires python3 with the `neovim` package installed.
