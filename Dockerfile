FROM ubuntu:18.04
MAINTAINER "Miki Yutani" mkyutani@gmail.com

# external build arguments

ARG crontab_template
ARG redis_host
ARG redis_port
ARG logs_dir
ARG slack_bot_token

# local build arguments

ARG crontab_template_path=/etc/sitewatcher-crontab.template
ARG crontab_path=/etc/cron.d/99sitewatcher

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

COPY ${crontab_template} ${crontab_template_path}

RUN touch ${crontab_path} && \
    chmod 0644 ${crontab_path} && \
    echo "REDIS_HOST=${redis_host}" >>${crontab_path} && \
    echo "REDIS_PORT=${redis_port}" >>${crontab_path} && \
    echo "LOGS_DIR=${logs_dir}" >>${crontab_path} && \
    echo "SLACK_BOT_TOKEN=${slack_bot_token}" >>${crontab_path} && \
    cat <${crontab_template_path} >>${crontab_path} && \
    crontab ${crontab_path}

ENTRYPOINT ["tail", "-f", "/logs/console.log"]

