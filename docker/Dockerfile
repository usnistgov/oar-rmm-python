FROM oar-metadata/ejsonschema

RUN apt-get update && apt-get install -y python-yaml curl wget less sudo zip \
                                         p7zip-full ca-certificates git
# RUN pip install --upgrade pip setuptools
RUN pip install funcsigs 'bagit>=1.6.3,<2.0' 'fs>=2.0.21' jsonpatch mako

RUN sed --in-place -e '/CREATE_MAIL_SPOOL/ s/=yes/=no/' /etc/default/useradd
ARG devuser=developer
ARG devuid=1000
RUN grep -qs :${devuid}: /etc/group || \
    groupadd --gid $devuid $devuser
RUN grep -Pqs ":${devuid}:\d+:" /etc/passwd || \
    useradd -m --comment "OAR Developer" --shell /bin/bash \
            --gid $devuid --uid $devuid $devuser
RUN echo $devuser "ALL=(ALL)" NOPASSWD:ALL > /etc/sudoers.d/90-developers

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod a+rx /usr/local/bin/entrypoint.sh

VOLUME /dev/oar-rmm-python
VOLUME /app/dist

RUN mkdir -p /dev/oar-rmm-python /app && chmod a+rwx /app
WORKDIR /dev/oar-rmm-python

# Update Python path for the RMM app
ENV PYTHONPATH /dev/oar-rmm-python/app:/app/dist/oar-rmm-python

ARG devuser=developer
USER $devuser

EXPOSE 7000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]