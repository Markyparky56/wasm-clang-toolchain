@echo off
set "__wasmclangdir=%~dp0"
set "PATH='%PATH%;%__wasmclangdir%ninja;%__wasmclangdir%binaryen/build/bin;%__wasmclangdir%llvm-project/build/bin;%__wasmclangdir%wabt/build/bin"