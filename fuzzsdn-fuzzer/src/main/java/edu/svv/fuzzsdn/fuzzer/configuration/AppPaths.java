package edu.svv.fuzzsdn.fuzzer.configuration;

import edu.svv.fuzzsdn.common.utils.Utils;
import net.harawata.appdirs.AppDirs;
import net.harawata.appdirs.AppDirsFactory;

import java.nio.file.Path;

public final class AppPaths
{
    private static final String APP_NAME = "fuzzsdn";

    private static AppDirs appDirs()
    {
        return AppDirsFactory.getInstance();
    }

    /**
     * Returns the user data directory path object.
     * @return the {@link Path} to the data directory.
     */
    public static Path userDataDir()
    {
        return Path.of(appDirs().getUserDataDir(APP_NAME, null, null));
    }

    /**
     * Returns the user cache directory path object.
     * @return the {@link Path} to the cache directory.
     */
    public static Path userCacheDir()
    {
        return Path.of(appDirs().getUserCacheDir(APP_NAME, null, null));
    }

    /**
     *
     */
    public static Path userStateDir()
    {
        // Get the home directory
        String stateDir = System.getenv("XDG_STATE_HOME");
        if (Utils.isNullOrEmpty(stateDir))
        {
            String homeDir  = System.getProperty("user.home");
            stateDir = homeDir + "/.local/state";
        }
        return Path.of(stateDir);
    }

    /**
     * Returns the user configuration directory path object.
     * @return the {@link Path} to the configuration directory.
     */
    public static Path userConfigDir()
    {
        return Path.of(appDirs().getUserConfigDir(APP_NAME, null, null));
    }

    /**
     * Returns the user configuration file path object.
     * @return the {@link Path} to the configuration file.
     */
    public static Path userConfigFile()
    {
        return userConfigDir().resolve("fuzzsdn-fuzzer.cfg");
    }

    /**
     * Returns the user log directory path object.
     * @return the {@link Path} to the log directory file.
     */
    public static Path userLogDir()
    {
        return userStateDir().resolve(APP_NAME + "/log");
    }

}
