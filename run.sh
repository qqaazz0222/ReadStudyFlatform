mkdir -p logs
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null ; then
    read -p "Port 5000 is already in use. Do you want to kill the process? (y/n): " answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        kill $(lsof -t -i:5000)
        echo "Process on port 5000 has been killed."
    else
        echo "Exiting without killing the process."
        exit 1
    fi
fi
source $(conda info --base)/etc/profile.d/conda.sh
conda activate read-study-platform 
nohup python main.py > logs/main.log 2>&1 &
echo "Server started on port 5000. Logs are being written to logs/main.log."