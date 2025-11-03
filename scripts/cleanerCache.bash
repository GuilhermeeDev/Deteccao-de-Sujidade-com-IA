BASE_DIR="${1:-.}"
echo "Limpando pastas __pycache__: $BASE_DIR"
find "$BASE_DIR" -type d -name "__pycache__" ! -path "*/venv/*" | while read -r dir; do
    echo "Removendo $dir"
    rm -rf "$dir"
done
echo "Limpeza concluída."