How to generate SSL certificates for AMQPNet.Lite client authentication with an 
ActiveMQ broker

Prerequisites:
==============
  * The script requires the "keytool" utility that is readily available 
    from a java jdk installation.
  * The script also uses dos2unix that is available in cygwin among 
    other places.

Setup:
======
    ActiveMQ Broker keystore and truststore files
	---------------------------------------------
    The generated keystore and truststore files are added to the broker 
    configuration: 

  <sslContext>
    <sslContext
      keyStore="${activemq.conf}/../keys/broker-jks.keystore" keyStorePassword="password"
      trustStore="${activemq.conf}/../keys/broker-jks.truststore" trustStorePassword="password"/>
  </sslContext>

The keystore and truststore files do not need to be installed or 
placed into any special store. The broker requires read-only access 
to the files at startup.

    ActiveMQ Broker AMQP SSL Connector
	----------------------------------
    The broker needs to have an amqps connector defined with the 
    needClientAuth switch set. 

  <transportConnector name="amqps" uri="amqp+ssl://0.0.0.0:5671?needClientAuth=true"/>

    Client certificates on client Windows system
	--------------------------------------------
    ** ca.crt is installed in the Trusted Root Certificate Authorities store.
    ** client.p12 is installed in the Personal Certificates store.
    ** client.crt is the cert file loaded in the client factory setup code:
       factory.SSL.ClientCertificates.Add(
          X509Certificate.CreateFromCertFile(certfile));

Other notes:
============
    ** Script variable BROKER_CN must be the fully qualified domain name 
       of the broker host.
    ** Script variable CLIENT_CN must be the name of the authenticated 
       user in the broker.
    ** The user must still pass the correct username and password 
       credentials in the connection Address.
    ** Windows Server 2012 R2 client system accepted certificates generated
       with "-keyalg RSA".
    ** File client.crt did not work without being processed by dos2unix.
