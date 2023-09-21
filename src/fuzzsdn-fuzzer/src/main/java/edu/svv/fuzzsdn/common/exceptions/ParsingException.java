package edu.svv.fuzzsdn.common.exceptions;

public class ParsingException extends Exception
{
    public ParsingException() {
        super();
    }

    public ParsingException(final String message, final Throwable cause) {
        super(message, cause);
    }

    public ParsingException(final String message) {
        super(message);
    }

    public ParsingException(final Throwable cause) {
        super(cause);
    }
}
