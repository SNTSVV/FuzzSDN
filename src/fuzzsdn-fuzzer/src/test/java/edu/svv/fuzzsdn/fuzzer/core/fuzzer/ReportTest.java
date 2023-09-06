package edu.svv.fuzzsdn.fuzzer.core.fuzzer;

import edu.svv.fuzzsdn.common.openflow.PktStruct;
import edu.svv.fuzzsdn.fuzzer.Report;
import edu.svv.fuzzsdn.fuzzer.instructions.actions.MutateBytesAction;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.math.BigInteger;

class ReportTest
{

    @Test
    void constructor_createSameReport_whenCopyingAnotherOne()
    {
        ByteBuf initialPacket   = Unpooled.wrappedBuffer(new byte[]{0x0, 0x1, 0x2});
        ByteBuf finalPacket     = Unpooled.wrappedBuffer(new byte[]{0xA, 0xB, 0xC});

        Report originalReport = new Report();
        originalReport.setPktStruct(new PktStruct(new PktStruct.Field("test", 0, 1)));
        originalReport.setInitialPacket(initialPacket);
        originalReport.setFinalPacket(finalPacket);
        originalReport.setCurrentAction(new MutateBytesAction.Builder().includeHeader(true).build());
        originalReport.addMutation(Report.MutationType.RANDOM_MUTATION, "test", BigInteger.ZERO, BigInteger.TEN);
        originalReport.addMutation(Report.MutationType.RANDOM_MUTATION, "test", BigInteger.TEN, BigInteger.TWO);
        originalReport.setEnd();

        Report copyReport = new Report(originalReport);

        Assertions.assertEquals(originalReport.getStart()              , copyReport.getStart());
        Assertions.assertEquals(originalReport.getEnd()                , copyReport.getEnd());
        Assertions.assertEquals(originalReport.getPktStruct()          , copyReport.getPktStruct());
        Assertions.assertArrayEquals(originalReport.getInitialPacket() , copyReport.getInitialPacket());
        Assertions.assertArrayEquals(originalReport.getFinalPacket()   , copyReport.getFinalPacket());
        Assertions.assertEquals(originalReport.getMutations()          , copyReport.getMutations());
    }

    @Test
    void setInitialPacket_doesNotThrowAnException_whenSettingANullInitialPacket()
    {
        Report testReport = new Report();
        testReport.setInitialPacket(null);
    }
}