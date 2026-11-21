# Instructions for using CAVE with MecwayBridge
## Install WSL (Windows subsystem für Linux)
```
wsl --install -d Ubuntu
```
Restart windows and open ubuntu
```
wsl -d Ubuntu
```
inside Ubuntu:
```
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl ca-certificates
sudo usermod -aG docker $USER
```
## Install CAVE
```
sh -c "$(curl -fsSL https://raw.githubusercontent.com/simvia-tech/cave/main/tools/install.sh)"
```
## verifiy Installation
```
cave --version
cave use stable
cave run -- --help
```
