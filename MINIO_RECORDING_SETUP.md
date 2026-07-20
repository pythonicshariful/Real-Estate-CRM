# MinIO Call Recording Storage Setup

Detailed guide for configuring and utilizing MinIO for call recording storage within the Southeast Landmark CRM.

## What is MinIO?
MinIO is a high-performance, self-hosted, S3-compatible object storage server. It runs as an independent Docker container alongside your CRM application, providing a secure, scalable, and fully controlled environment for storing sensitive audio files such as customer call recordings.

## Initial Setup
1. MinIO starts automatically when you run `docker-compose up -d`.
2. Access the MinIO web console at `http://localhost:9001` (or your domain's mapped equivalent).
3. Login using the credentials defined in your `.env` file: `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY`.
4. The system is designed to automatically provision two buckets upon initialization: `recordings` (for audio files) and `backups` (for database dumps).

## How Recordings Work
1. When a field executive completes a customer call, they utilize the CRM interface to upload the call recording file.
2. The file is directly stored in the MinIO `recordings` bucket using an organized, hierarchical path structure: `{opportunity_id}/{date}/{call_log_id}.mp3`.
3. The actual filenames within MinIO are encrypted. No direct public URLs are ever exposed or accessible.
4. When an authorized user (like a Manager or Administrator) requests to listen to a recording, the CRM backend dynamically generates a 15-minute presigned S3 URL.
5. This URL expires automatically after the 15-minute window, ensuring that the link cannot be indefinitely shared, bookmarked, or leaked.
6. For compliance and auditing, every single download or playback request is strictly logged to the `RecordingDownloadLog` database table, capturing the user ID, timestamp, and IP address.

## Permissions & Access Control
- **Executives:** Can only upload recordings. They are restricted to viewing and accessing data pertaining only to their assigned calls.
- **Managers:** Can listen to and download recordings for all team members under their direct supervision.
- **GM/CEO:** Have comprehensive full access to all recordings across the organization.
- **Admin:** Possess technical access to manage the storage infrastructure but lack permission to access or playback the actual audio content, ensuring privacy.

## Production Storage Expansion
As your CRM scales, your storage requirements will grow. MinIO is built for the enterprise and offers several expansion paths:
- MinIO supports clustering for high availability and load balancing.
- Native mirroring features allow you to seamlessly synchronize buckets to AWS S3 or Google Cloud Storage for off-site disaster recovery.
- You can establish bucket lifecycle policies directly from the MinIO console (e.g., automatically deleting or archiving recordings older than 2 years to conserve active disk space).

## Security
- The MinIO container is not exposed directly to the public internet. It resides safely within the internal Docker bridge network (`crm_network`).
- All external access to objects flows securely through the CRM backend via temporary, presigned URLs.
- Bucket policies are strictly set to deny all public access by default.
- For enhanced compliance, you can enable MinIO encryption at rest by setting the `MINIO_KMS_SECRET_KEY` variable in your `docker-compose.yml` environment block.
