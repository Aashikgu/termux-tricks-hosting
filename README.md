# termux-tricks-hosting

📦 Installation Commands
Copy and paste the following commands one by one:

Update all packages
pkg update && pkg upgrade -y
pkg install wget curl openssh git php python python3 cloudflared -y
wget https://github.com/debzero/Hosting/raw/refs/heads/main/Hosting.tar.gz
Setup Comands
tar -xzvf Hosting.tar.gz;
rm Hosting.tar.gz;
chmod +x host
mv host $PREFIX/bin
Server Start Type host
host
📌 Contact Me