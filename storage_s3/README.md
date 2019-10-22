# S3 Storage Plugin

The S3 storage plugin allows Indico to store materials etc. on [Amazon S3][amazon-s3] or
an S3-compatible object storage service (Ceph S3, Minio, etc.) instead of the local file
system.

## Warning

This plugin has only been tested with Ceph S3 so far. So if you encounter any problems
using e.g. the real Amazon S3, please let us know!

It is currently used in production on multiple Indico instances, so we believe it is
stable, but please be advised that we do not provide a way to move files back from S3
to local storage (but it would of course be possible to write a script for this).

## Configuration

Configuration is done using the `STORAGE_BACKENDS` entry of `indico.conf`; add a new key
with a name of your choice (e.g. `s3`) and specify the details of the S3 storage in the
value.

For a single bucket, all you need to specify is the bucket name: 

```python
STORAGE_BACKENDS = {
    # ...
    's3': 's3:bucket=indico-test'
}
```

If you want to dynamically create buckets for each year, month or week, you can do this
as well. A task will automatically create new buckets a while before it will become active.


```python
STORAGE_BACKENDS = {
    # ...
    's3': 's3-dynamic:bucket_template=indico-test-<year>,bucket_secret=somethingrandom'
}
```

For authentication and general S3 config (e.g. to use subdomains for bucket names), the
preferred way is to use the standard files, i.e. `~/.aws/credentials` and `~/.aws/config`,
but you can also specify all settings in the storage backend entry like this:

```python
STORAGE_BACKENDS = {
    # ...
    's3': 's3:bucket=my-indico-test-bucket,access_key=12345,secret_key=topsecret'
}
```

### Available config options

Multiple options can be specified by separating them with commas. These options are available:

- `host` -- the host where S3 is running, in case you use a custom S3-compatible storage.
- `profile` -- the name of a specific S3 profile (used in the `~/.aws/` config files)
- `access_key` -- the S3 access key; should not be used in favor of `~/.aws/credentials`
- `secret_key` -- the S3 access key; should not be used in favor of `~/.aws/credentials`
- `addressing_style` -- the S3 addressing style (`virtual` or `path`); should not be used in
  favor of `~/.aws/config`
- `bucket_policy_file` -- the path to a file containing an S3 bucket policy; this only applies
  to new buckets created by this plugin
- `bucket_versioning` -- whether to enable S3 versioning on the bucket; this only applies to new
  buckets created by this plugin
- `proxy` -- whether to proxy downloads. If set to `true`, all files will be downloaded to memory
  and then sent to the client by Indico. This may have performance implications if you have large
  files. A better option is setting it to `nginx`, which requires some extra configuration (see below),
  but lets nginx handle proxying downloads transparently. If you do not use proxying at all,
  downloading a file redirects the user to a temporary S3 URL valid for a few minutes. Generally
  this works fine, but it may result in people accidentally copying (and forwarding) temporary
  links that expire quickly.
- `meta` -- a custom string that is included in the bucket info API of the plugin. You generally do
  not need this unless you are using custom scripts accessing that API and want to include some
  extra data there.

When using the `s3` backend (single static bucket), the following extra option is available:

- `bucket` (required) -- the name of the bucket

When using the `s3-dynamic` backend, the following extra options are available:

- `bucket_template` (required) -- a template specifying how the bucket names should be generated.
  Needs to contain at least one of `<year>`, `<month>` or `<week>`
- `bucket_secret` (required unless set in aws config) -- a random secret used to make bucket names
  unguessable (as bucket names need to be globally unique on S3); may also be specified as
  `indico_bucket_secret` in `~/.aws/credentials`

## Proxying downloads through nginx

If you want to use the `proxy=nginx` option to avoid redirecting users to the actual S3 URL
for file downloads without having the extra load and memory usage of downloading a (possibly
large) attachment to memory first that comes with `proxy=on`, you need to add the following
to the `server` block in your nginx config that is responsible for Indico.

```nginx
location ~ ^/.xsf/s3/(https?)/([^/]+)/(.+)$ {
        internal;
        set $download_protocol $1;
        set $download_host $2;
        set $download_path $3;
        set $download_url $download_protocol://$download_host/$download_path;
        resolver YOUR_RESOLVER;
        proxy_set_header Host $download_host;
        proxy_set_header Authorization '';
        proxy_set_header Cookie '';
        proxy_hide_header X-Amz-Request-Id;
        proxy_hide_header Bucket;
        proxy_max_temp_file_size 0;
        proxy_intercept_errors on;
        error_page 301 302 307 = @s3_redirect;
        proxy_pass $download_url$is_args$args;
}

location @s3_redirect {
        internal;
        resolver YOUR_RESOLVER;
        set $saved_redirect_location '$upstream_http_location';
        proxy_pass $saved_redirect_location;
}
```

Replace `YOUR_RESOLVER` with the hostname or IP address of a nameserver nginx can use to
resolve the S3 hosts. You may find a suitable IP in your `/etc/resolv.conf` or by asking
someone from your IT department. If you are running a local caching nameserver, `localhost`
would work as well.

If you are interested in how this works, check [this blog post][nginx-blog] on which this
config is based.

## Migration of existing data

The plugin comes with a migration tool, accessible through the `indico s3 migrate` CLI.
It can be used without downtime of your service as it consists of two steps - first copying
the files, and then updating references in your database. Please have a look at its `--help`
output if you want to use it; we did not have time to write detailed documentation for it yet.

The step that updates the database can be reversed in case you want to switch back from S3
to local storage for whatever reason, but it will only affect migrated files - any file stored
directly on S3 later (and thus not present on the local file system), will not be reverted.
You would need to write your own script that downloads those files from S3.


[amazon-s3]: https://aws.amazon.com/s3/
[nginx-blog]: https://www.mediasuite.co.nz/blog/proxying-s3-downloads-nginx/
