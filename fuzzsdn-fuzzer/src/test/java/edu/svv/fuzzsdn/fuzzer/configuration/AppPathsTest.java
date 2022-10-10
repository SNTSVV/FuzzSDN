package edu.svv.fuzzsdn.fuzzer.configuration;

import org.junit.jupiter.api.Test;

class AppPathsTest
{

    @Test
    void sharedDir()
    {
        System.out.println(System.getenv("XDG_STATE_HOME"));
        System.out.println(AppPaths.userStateDir());
        System.out.println(AppPaths.userLogDir());
    }

    @Test
    void userDataDir()
    {
    }

    @Test
    void siteDataDir()
    {
    }

    @Test
    void userCacheDir()
    {
    }

    @Test
    void userStateDir()
    {
    }

    @Test
    void userConfigDir()
    {
    }

    @Test
    void userConfigFile()
    {
    }

    @Test
    void siteConfigDir()
    {
    }

    @Test
    void userLogDir()
    {
    }
}