FROM ubuntu:18.04
MAINTAINER "Miki Yutani" mkyutani@gmail.com

# external build arguments

ARG crontab_template
ARG redis_host
ARG redis_port
ARG logs_dir
ARG slack_bot_token

# basic configuration

RUN apt update && \
    apt install -y language-pack-ja-base language-pack-ja locales git python3 python3-pip cron
RUN locale-gen ja_JP.UTF-8
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP.UTF-8
ENV LC_ALL ja_JP.UTF-8

# install sitewatcher

RUN git clone https://github.com/mkyutani/sitewatcher.git
RUN cd sitewatcher && \
    pip3 install .
RUN mkdir /logs

# environment variables

ENV REDIS_HOST=${redis_host}
ENV REDIS_PORT=${redis_port}
ENV LOGS_DIR=${logs_dir}
ENV SLACK_BOT_TOKEN=${slack_bot_token}

# start cron

COPY ${crontab_template} /etc
RUN export crontab_template_basename=$(/usr/bin/basename ${crontab_template}) && \
    touch /etc/cron.d/99sitewatcher && \
    chmod 0644 /etc/cron.d/99sitewatcher && \
    echo "REDIS_HOST=${redis_host}" >>/etc/cron.d/99sitewatcher && \
    echo "REDIS_PORT=${redis_port}" >>/etc/cron.d/99sitewatcher && \
    echo "LOGS_DIR=${logs_dir}" >>/etc/cron.d/99sitewatcher && \
    echo "SLACK_BOT_TOKEN=${slack_bot_token}" >>/etc/cron.d/99sitewatcher && \
    cat /etc/${crontab_template_basename} >>/etc/cron.d/99sitewatcher && \
    crontab /etc/cron.d/99sitewatcher

ENTRYPOINT ["tail", "-f", "/logs/console.log"]

