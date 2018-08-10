package com.iafisher;


public class Server {
    public String getGreeting() {
        return "Hello world.";
    }

    public static void main(String[] args) {
        System.out.println(new Server().getGreeting());
    }
}
