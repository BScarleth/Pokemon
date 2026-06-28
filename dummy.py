import kagglehub

# Download latest version
path = kagglehub.dataset_download("kiyotah/cg-lib")

print("Path to dataset files:", path)