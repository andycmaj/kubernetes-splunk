FROM alpine:3.4

RUN apk update \
 && apk add bash rsync python py-pip zip \
 && pip install awscli \
 && apk --purge -v del py-pip \
 && rm /var/cache/apk/*

ENV BACKUP_PATH /opt/backup
ENV SPLUNK_CONFIG_PATH /opt/splunk/etc

COPY backup.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/backup.sh

COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT [ "entrypoint.sh" ]
