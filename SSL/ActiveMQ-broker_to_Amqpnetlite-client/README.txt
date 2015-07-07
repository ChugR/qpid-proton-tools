How to generate SSL certificates for Lite client authentication with an 
ActiveMQ broker

Prerequisites:
--------------
  * The script requires the "keytool" utility that is readily available 
    from java jdk.
  * The script also uses dos2unix [1] that is available in cygwin among 
    other places.

Setup:
------
    Broker keystore and truststore files.
    The generated keystore and truststore files are added to the broker 
    configuration: 

  <sslContext>
    <sslContext
      keyStore="${activemq.conf}/../keys/broker-jks.keystore" keyStorePassword="password"
      trustStore="${activemq.conf}/../keys/broker-jks.truststore" trustStorePassword="password"/>
  </sslContext>

The keystore and truststore files do not need to be installed or 
placed into any special store. On Windows (and Linux) the broker 
requires read-only access to the files at startup.

    The broker needs to have an amqps connector defined with the 
    needClientAuth switch set. 

<transportConnector name="amqps" uri="amqps://0.0.0.0:5671?maximumConnections=1000&amp;wireFormat.maxFrameSize=104857600&amp;needClientAuth=true"/>

    Client certificates
    ** ca.crt is installed in the client machine Trusted Root Certificate 
       Authorities store.
    ** client.p12 is installed in the client machine Personal Certificates store.
    ** client.crt is the cert file loaded in the 
       factory.SSL.ClientCertificates.Add(
          X509Certificate.CreateFromCertFile(certfile)) setup function.

Other notes:
------------
    ** Script variable BROKER_CN must be the fully qualified domain name 
       of the broker host.
    ** Script variable CLIENT_CN must be the name of the authenticated 
       user in the broker.
    ** The user must still pass the correct username and password 
       credentials in the connection Address.
    ** My Windows Server 2012 R2 client system required -keyalg RSA. 
       to generate usable certificates.

As usual, there are plenty of other ways to get this working using 
different tools (openssl or certutil). I hope this gets you started 
with ActiveMQ.

[1] I was generating the client cert on a Linux system. The cert 
would not be accepted by amqpnetlite unless it was processed by 
dos2unix first. The same holds true if the cert is generated on a 
Windows system. This is the first file generated-on-linux 
fails-on-Windows fixed-by-dos2unix situation I've ever seen!