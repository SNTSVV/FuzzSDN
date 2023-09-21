package edu.svv.fuzzsdn.fuzzer;

import edu.svv.fuzzsdn.fuzzer.configuration.Configuration;
import org.apache.commons.lang3.time.StopWatch;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Scanner;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import static edu.svv.fuzzsdn.common.utils.Utils.isNullOrEmpty;


public class App
{
    private static final Logger log = LoggerFactory.getLogger(App.class);
    private static final StopWatch watch = new StopWatch();

    @SuppressWarnings("BusyWait")
    public static void main(String[] args)
    {
        //
        watch.start();

        // Configure create first instance of config to init it
        Configuration config = Configuration.getInstance();


        // Verify Controller IP and Mininet IP
        Scanner scanner = new Scanner(System.in);
        if (isNullOrEmpty(config.get("SDNSwitchIP")))
        {
            System.out.println("No IP for Mininet Machine found the configuration file.\nPlease, select the IP");
            config.set("SDNSwitchIP", scanner.nextLine());
        }
        if (isNullOrEmpty(config.get("SDNControllerIP")))
        {
            System.out.println("No IP for Mininet Machine found the configuration file.\nPlease, select the IP");
            config.set("SDNControllerIP", scanner.nextLine());
        }


        // Register the shutdown hook, so the program tries to exit gracefully if there is a shutdown
        Runtime.getRuntime().addShutdownHook(new Thread(App::shutdown));

        // Get core instance and start it
        Core.getInstance().start();

        // Infinite loop so the program runs forever
        while (!Thread.currentThread().isInterrupted())
        {
            try
            {
                Thread.sleep(1500);
            }
            catch (InterruptedException e)
            {
                // Break out of the loop
                break;
            }
        }

    }

    public static void shutdown()
    {
        // Stops the core
        Core.getInstance().stop();

        // Print execution time
        watch.stop();
        log.debug("Execution time: {}s", watch.getTime(TimeUnit.MILLISECONDS) / 1000d);

        // If there are some leftover threads, display them in TRACE for debug purpose
        if (log.isTraceEnabled())
        {
            StringBuilder sb = new StringBuilder();
            sb.append("Listing all remaining threads left before application shutdown:\n");
            Set<Thread> threadSet = Thread.getAllStackTraces().keySet();
            for (Thread t : threadSet)
            {
                sb.append("ID: ").append(t.getId()).append(" - ");
                sb.append("Name: ").append(t.getName()).append("\n");
                StackTraceElement[] stacks = t.getStackTrace();
                for (StackTraceElement s : stacks)
                {
                    sb.append("\t").append(s.toString()).append("\n");
                }
            }
            log.trace(sb.toString());
        }

        log.info("PacketFuzzer has stopped.");
    }
}
