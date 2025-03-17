In Terraform, the archive_file data source does not automatically detect content changes if the file name remains the same. However, you can force Terraform to detect changes by using a content hash or a timestamp() workaround.

Solution 1: Use content_base64 Instead of source_file
Instead of relying on source_file, use the file's content as input. This ensures Terraform detects content changes.

hcl
Copy
Edit
data "local_file" "my_file" {
  filename = "my-file.txt"
}

data "archive_file" "zip" {
  type        = "zip"
  output_path = "my-file.zip"

  source {
    content  = data.local_file.my_file.content
    filename = "my-file.txt"
  }
}
✅ Why?

local_file reads the file content.
Any change in content triggers an update in archive_file.
Solution 2: Use md5() or sha256() Hash to Force Changes
Calculate the hash of the file and use it in archive_file.

hcl
Copy
Edit
data "local_file" "my_file" {
  filename = "my-file.txt"
}

resource "null_resource" "file_change_trigger" {
  triggers = {
    file_hash = md5(data.local_file.my_file.content)
  }
}

data "archive_file" "zip" {
  type        = "zip"
  output_path = "my-file-${md5(data.local_file.my_file.content)}.zip"

  source {
    content  = data.local_file.my_file.content
    filename = "my-file.txt"
  }

  depends_on = [null_resource.file_change_trigger]
}
✅ Why?

The md5() function generates a hash based on file content.
If the file changes, the hash changes, forcing archive_file to update.
Solution 3: Append timestamp() to output_path
Another workaround is appending timestamp() to force a refresh.

hcl
Copy
Edit
data "archive_file" "zip" {
  type        = "zip"
  output_path = "my-file-${timestamp()}.zip"

  source_file = "my-file.txt"
}
⚠️ Note: This will regenerate the archive on every apply, even if the file content hasn't changed.

