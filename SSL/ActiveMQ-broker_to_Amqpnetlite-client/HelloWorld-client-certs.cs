//  ------------------------------------------------------------------------------------
//  Copyright (c) 2015 Red Hat, Inc.
//  All rights reserved.
//
//  Licensed under the Apache License, Version 2.0 (the ""License""); you may not use this
//  file except in compliance with the License. You may obtain a copy of the License at
//  http://www.apache.org/licenses/LICENSE-2.0
//
//  THIS CODE IS PROVIDED *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
//  EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED WARRANTIES OR
//  CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE, MERCHANTABLITY OR
//  NON-INFRINGEMENT.
//
//  See the Apache Version 2.0 License for specific language governing permissions and
//  limitations under the License.
//  ------------------------------------------------------------------------------------

//
// HelloWorld-client-certs
//
// Command line:
//   HelloWorld-client-certs [brokerUrl [brokerEndpointAddress]]
//
// Default:
//   HelloWorld-client-certs amqps://client:password@host.example.com:5671 amq.topic
//
// Requires:
//   An authenticated, SSL broker or peer at the brokerUrl 
//   capable of receiving and delivering messages through 
//   the endpoint address.
//
using System;
using System.Linq;
using Amqp;
using Amqp.Framing;
using Amqp.Types;
using System.Security;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Security.Permissions;
using System.Threading;
using System.Threading.Tasks;

namespace HelloWorld_client_certs
{
    class HelloWorld_client_certs
    {
        static async Task<int> SslConnectionTestAsync(string brokerUrl, string address, string certfile)
        {
            try
            {
                ConnectionFactory factory = new ConnectionFactory();
                factory.TCP.NoDelay = true;
                factory.TCP.SendBufferSize = 16 * 1024;
                factory.TCP.SendTimeout = 30000;
                factory.TCP.ReceiveBufferSize = 16 * 1024;
                factory.TCP.ReceiveTimeout = 30000;

                factory.SSL.RemoteCertificateValidationCallback = (a, b, c, d) => true;
                factory.SSL.ClientCertificates.Add(X509Certificate.CreateFromCertFile(certfile));
                factory.SSL.CheckCertificateRevocation = false;
                
                factory.AMQP.MaxFrameSize = 64 * 1024;
                factory.AMQP.HostName = "host.example.com";
                factory.AMQP.ContainerId = "amq.topic";

                Address sslAddress = new Address(brokerUrl);
                Connection connection = await factory.CreateAsync(sslAddress);

                Session session = new Session(connection);
                SenderLink sender = new SenderLink(session, "sender1", address);
                ReceiverLink receiver = new ReceiverLink(session, "helloworld-receiver", address);

                Message helloOut = new Message("Hello - using client cert");
                await sender.SendAsync(helloOut);

                Message helloIn = await receiver.ReceiveAsync();
                receiver.Accept(helloIn);

                await connection.CloseAsync();

                Console.WriteLine("{0}", helloIn.Body.ToString());

                Console.WriteLine("Press enter key to exit...");
                Console.ReadLine();
                return 0;
            }
            catch (Exception e)
            {
                Console.WriteLine("Exception {0}.", e);
                return 1;
            }
        }

        static void Main(string[] args)
        {
            string broker = args.Length >= 1 ? args[0] : "amqps://client:password@host.example.com:5671";
            string address = args.Length >= 2 ? args[1] : "amq.topic";
//            Trace.TraceLevel = TraceLevel.Frame;
//            Trace.TraceListener = (f, a) => Console.WriteLine(DateTime.Now.ToString("[hh:ss.fff]") + " " + string.Format(f, a));

            Task<int> task = SslConnectionTestAsync(broker, address, "D:\\FULL\\PATH\\TO\\client.crt");
            task.Wait();
        }
    }
}
