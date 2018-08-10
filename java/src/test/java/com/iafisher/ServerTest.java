package com.iafisher;

import org.junit.Test;
import static org.junit.Assert.assertNotNull;


public class ServerTest {
    @Test public void testAppHasAGreeting() {
        Server classUnderTest = new Server();
        assertNotNull("app should have a greeting", classUnderTest.getGreeting());
    }
}
