package edu.svv.fuzzsdn.common.exceptions;

/**
 * Thrown to indicate that a block of code has not been implemented.
 * This exception supplements {@link RuntimeException} so it doesn't need to be catched added to the method
 * signature
 */
public class NotImplementedException extends RuntimeException
{
    /**
     * Constructs a NotImplementedException with no detail message
     */
    public NotImplementedException()
    {
        super();
    }

    /**
     * Constructs an UnsupportedOperationException with the specified detail message.
     * @param message – the detail message
     */
    public NotImplementedException(String message)
    {
        super(message);
    }

    /**
     * Constructs a new exception with the specified cause and a detail message of
     * {@code (cause==null ? null : cause.toString())} (which typically contains the class and detail message of
     * {@code cause}). This constructor is useful for exceptions that are little more than wrappers for other throwables
     * (for example, {@link java.security.PrivilegedActionException}).
     *
     * @param  cause the cause (which is saved for later retrieval by the {@link Throwable#getCause()} method).(A
     *               {@code null} value is permitted, and indicates that the cause is nonexistent or unknown.)
     */
    public NotImplementedException(Throwable cause)
    {
        super(cause);
    }

    /**
     * Constructs a new exception with the specified detail message and cause.
     * Note that the detail message associated with cause is not automatically incorporated in this exception's detail
     * message.
     * @param message the detail message (which is saved for later retrieval by the {@link Throwable#getMessage()}
     *                method).
     * @param cause the cause (which is saved for later retrieval by the {@link Throwable#getCause()} method).
     *              (A {@code null} value is permitted, and indicates that the cause is nonexistent or unknown.)
     */
    public NotImplementedException(String message, Throwable cause)
    {
        super(message, cause);
    }
}