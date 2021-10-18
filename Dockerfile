FROM ubuntu:18.04
RUN apt-get update \
    && apt-get install -y git python3 python3-pip cron
RUN git clone https://github.com/mkyutani/sitewatcher.git
RUN cd sitewatcher \
    && pip3 install .
RUN mkdir /logs
ENTRYPOINT ["cron", "-f"]



